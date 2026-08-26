import csv,io,os,sqlite3,subprocess,sys,tempfile,unittest,zipfile
from pathlib import Path
from scripts.active.import_gtfs_stop_structure import create_tables,import_stop_structure
ROOT=Path(__file__).resolve().parents[1]
def feed(path,version="v1"):
 fields=["stop_id","stop_code","stop_name","stop_lat","stop_lon","location_type","parent_station","platform_code","zone_id","wheelchair_boarding"]
 rows=[dict(zip(fields,["P","","Station","38","-77","1","","","Z","1"])),dict(zip(fields,["A","100","Bay A","38.1","-77.1","0","P","A","Z","2"])),dict(zip(fields,["O","","Orphan","","bad","0","MISSING","","",""]))]
 s=io.StringIO();w=csv.DictWriter(s,fieldnames=fields);w.writeheader();w.writerows(rows)
 i=io.StringIO();w=csv.DictWriter(i,fieldnames=["feed_publisher_name","feed_version"]);w.writeheader();w.writerow({"feed_publisher_name":"Transit","feed_version":version})
 with zipfile.ZipFile(path,"w") as z:z.writestr("stops.txt",s.getvalue());z.writestr("feed_info.txt",i.getvalue())
class Tests(unittest.TestCase):
 def setUp(self): self.t=tempfile.TemporaryDirectory();self.r=Path(self.t.name);self.db=self.r/"x.db";self.zip=self.r/"x.zip";feed(self.zip)
 def tearDown(self): self.t.cleanup()
 def test_idempotent_schema_and_snapshot(self):
  self.assertEqual(3,import_stop_structure(self.db,self.zip,"one")["inserted"]);self.assertEqual(0,import_stop_structure(self.db,self.zip,"one")["inserted"])
  c=sqlite3.connect(self.db);create_tables(c);create_tables(c);self.assertEqual((1,3),(c.execute("select count(*) from gtfs_feed_snapshots").fetchone()[0],c.execute("select count(*) from gtfs_stop_structure").fetchone()[0]));c.close()
 def test_fields_nulls_and_parent_flags(self):
  import_stop_structure(self.db,self.zip,"one");c=sqlite3.connect(self.db);self.assertEqual(("100","P","A","0","Z","2"),c.execute("select stop_code,parent_station,platform_code,location_type,zone_id,wheelchair_boarding from gtfs_stop_structure where gtfs_stop_id='A'").fetchone());r=c.execute("select stop_lat,stop_lon,quality_flags from gtfs_stop_structure where gtfs_stop_id='O'").fetchone();self.assertEqual((None,"bad"),r[:2]);self.assertIn("unresolved_parent_station",r[2]);c.close()
 def test_feed_local_ids_and_versions_coexist(self):
  import_stop_structure(self.db,self.zip,"one");import_stop_structure(self.db,self.zip,"two");z=self.r/"v2.zip";feed(z,"v2");import_stop_structure(self.db,z,"one");c=sqlite3.connect(self.db);self.assertEqual(3,c.execute("select count(*) from gtfs_feed_snapshots").fetchone()[0]);self.assertEqual(3,c.execute("select count(*) from gtfs_stop_structure where gtfs_stop_id='A'").fetchone()[0]);c.close()
 def test_direct_command_honors_env_and_preserves_existing(self):
  c=sqlite3.connect(self.db);c.execute("create table physical_stops(id primary key)");c.execute("insert into physical_stops values(935)");c.commit();c.close();e=os.environ.copy();e["DMV_BUS_STOPS_DB"]=str(self.db);r=subprocess.run([sys.executable,"scripts/active/import_gtfs_stop_structure.py",str(self.zip),"--feed-id","one"],cwd=ROOT,env=e,text=True,capture_output=True);self.assertEqual(0,r.returncode,r.stderr);c=sqlite3.connect(self.db);self.assertEqual([(935,)],c.execute("select * from physical_stops").fetchall());c.close()
if __name__=="__main__":unittest.main()
