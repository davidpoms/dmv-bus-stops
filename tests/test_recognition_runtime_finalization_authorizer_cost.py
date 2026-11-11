"""R22 deterministic deny-policy equivalence; no lifecycle or authority."""
import ast
import inspect
import json
from pathlib import Path
import sqlite3
import statistics
import time
import unittest

from src.review.recognition import runtime_validation as validation


class FinalizationAuthorizerCostTests(unittest.TestCase):
    def test_same_policy_for_every_sqlite_action_and_table_category(self):
        # Reconstruct the previous function by replacing only the constant
        # membership expression with its original per-call comprehension.
        tree=ast.parse(inspect.getsource(validation._authentication_writes))
        class Previous(ast.NodeTransformer):
            def visit_Name(self,node):
                if node.id=='_AUTHENTICATION_DDL_DENY':
                    return ast.copy_location(ast.parse("{getattr(sqlite3,'SQLITE_'+name) for name in "
                        "('CREATE_INDEX','CREATE_TABLE','CREATE_TEMP_INDEX','CREATE_TEMP_TABLE',"
                        "'CREATE_TEMP_TRIGGER','CREATE_TEMP_VIEW','CREATE_TRIGGER','CREATE_VIEW',"
                        "'CREATE_VTABLE','DROP_INDEX','DROP_TABLE','DROP_TEMP_INDEX','DROP_TEMP_TABLE',"
                        "'DROP_TEMP_TRIGGER','DROP_TEMP_VIEW','DROP_TRIGGER','DROP_VIEW','DROP_VTABLE',"
                        "'ALTER_TABLE','ATTACH','DETACH')}",mode='eval').body,node)
                return node
        namespace=dict(validation.__dict__)
        exec(compile(ast.fix_missing_locations(Previous().visit(tree)),'previous_callback','exec'),namespace)
        previous=namespace['_authentication_writes']
        actions=set(range(40))|{getattr(sqlite3,n) for n in dir(sqlite3)
            if n.startswith('SQLITE_') and type(getattr(sqlite3,n)) is int}
        tables=('recognition_admin_primary','recognition_admin_sessions','recognition_admin_mfa',
            'recognition_admin_attempts','recognition_admin_audit','recognition_runtime_auth_bindings',
            'recognition_admin_stepups','recognition_admin_confirmations','arbitrary_target',None)
        for action in actions:
            for table in tables:
                self.assertEqual(previous(action,table),validation._authentication_writes(action,table))
        calls=[(x,'arbitrary_target') for x in (sqlite3.SQLITE_SELECT,sqlite3.SQLITE_READ,
               sqlite3.SQLITE_FUNCTION,sqlite3.SQLITE_PRAGMA)]*7500
        timings={}
        for name,fn in [('previous',previous),('constant',validation._authentication_writes)]:
            samples=[]
            for _ in range(3):
                start=time.perf_counter()
                for args in calls:fn(*args)
                samples.append(time.perf_counter()-start)
            timings[name]=dict(calls=len(calls),median_seconds=statistics.median(samples),samples=samples)
        path=Path(__file__).resolve().parents[1]/'.tmp'/'recognition-r22-authorizer-cost.json'
        path.write_text(json.dumps(timings,indent=2)+'\n',encoding='utf-8')
        self.assertIsInstance(validation._AUTHENTICATION_DDL_DENY,frozenset)
        self.assertEqual(21,len(validation._AUTHENTICATION_DDL_DENY))
