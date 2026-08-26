"""Preserve an immutable GTFS stops.txt snapshot; no current pipeline is rebuilt."""
import argparse,csv,hashlib,io,json,os,sqlite3,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
DEFAULT_DB=Path(os.environ.get("DMV_BUS_STOPS_DB",ROOT/"src/database/dmv_bus_stops.db"))
FIELDS=("stop_code","stop_name","stop_lat","stop_lon","location_type","parent_station","platform_code","zone_id","wheelchair_boarding")
SCHEMA="""
CREATE TABLE IF NOT EXISTS gtfs_feed_snapshots(id INTEGER PRIMARY KEY AUTOINCREMENT,feed_id TEXT NOT NULL,snapshot_sha256 TEXT NOT NULL,source_file TEXT NOT NULL,source_url TEXT,feed_publisher_name TEXT,feed_publisher_url TEXT,feed_lang TEXT,feed_start_date TEXT,feed_end_date TEXT,feed_version TEXT,imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,UNIQUE(feed_id,snapshot_sha256));
CREATE TABLE IF NOT EXISTS gtfs_stop_structure(id INTEGER PRIMARY KEY AUTOINCREMENT,snapshot_id INTEGER NOT NULL,gtfs_stop_id TEXT NOT NULL,stop_code TEXT,stop_name TEXT,stop_lat TEXT,stop_lon TEXT,location_type TEXT,parent_station TEXT,platform_code TEXT,zone_id TEXT,wheelchair_boarding TEXT,quality_flags TEXT NOT NULL DEFAULT '[]',raw_row_json TEXT NOT NULL,FOREIGN KEY(snapshot_id) REFERENCES gtfs_feed_snapshots(id),UNIQUE(snapshot_id,gtfs_stop_id));
CREATE INDEX IF NOT EXISTS idx_gtfs_stop_structure_feed_stop ON gtfs_stop_structure(snapshot_id,gtfs_stop_id);
CREATE INDEX IF NOT EXISTS idx_gtfs_stop_structure_parent ON gtfs_stop_structure(snapshot_id,parent_station);
CREATE INDEX IF NOT EXISTS idx_gtfs_stop_structure_stop_code ON gtfs_stop_structure(snapshot_id,stop_code);
"""
def create_tables(conn): conn.executescript(SCHEMA)
def clean(v): return None if v is None or str(v)=="" else str(v)
def read_rows(z,name,required=True):
 try: data=z.read(name)
 except KeyError:
  if required: raise RuntimeError(f"GTFS input is missing required {name}")
  return []
 return list(csv.DictReader(io.StringIO(data.decode("utf-8-sig"))))
def flags(row,ids):
 out=[];parent=clean(row.get("parent_station"))
 if parent and parent not in ids: out.append("unresolved_parent_station")
 for field in ("stop_lat","stop_lon"):
  value=clean(row.get(field))
  if value is None: out.append(f"null_{field}")
  else:
   try: float(value)
   except ValueError: out.append(f"malformed_{field}")
 return out
def import_stop_structure(db_path,feed_path,feed_id,source_url=None):
 feed_path=Path(feed_path)
 if not feed_path.is_file(): raise FileNotFoundError(f"GTFS ZIP not found: {feed_path}")
 payload=feed_path.read_bytes();digest=hashlib.sha256(payload).hexdigest().upper()
 with zipfile.ZipFile(io.BytesIO(payload)) as z: stops=read_rows(z,"stops.txt");info=(read_rows(z,"feed_info.txt",False) or [{}])[0]
 ids=[clean(r.get("stop_id")) for r in stops]
 if any(x is None for x in ids): raise RuntimeError("stops.txt contains a blank stop_id")
 if len(ids)!=len(set(ids)): raise RuntimeError("stops.txt contains duplicate stop_id values")
 idset=set(ids);conn=sqlite3.connect(db_path);conn.execute("PRAGMA foreign_keys=ON")
 try:
  with conn:
   create_tables(conn);conn.execute("INSERT OR IGNORE INTO gtfs_feed_snapshots(feed_id,snapshot_sha256,source_file,source_url,feed_publisher_name,feed_publisher_url,feed_lang,feed_start_date,feed_end_date,feed_version) VALUES(?,?,?,?,?,?,?,?,?,?)",(feed_id,digest,feed_path.name,source_url,*(clean(info.get(k)) for k in ("feed_publisher_name","feed_publisher_url","feed_lang","feed_start_date","feed_end_date","feed_version"))))
   sid=conn.execute("SELECT id FROM gtfs_feed_snapshots WHERE feed_id=? AND snapshot_sha256=?",(feed_id,digest)).fetchone()[0];before=conn.execute("SELECT COUNT(*) FROM gtfs_stop_structure WHERE snapshot_id=?",(sid,)).fetchone()[0]
   conn.executemany("INSERT OR IGNORE INTO gtfs_stop_structure(snapshot_id,gtfs_stop_id,stop_code,stop_name,stop_lat,stop_lon,location_type,parent_station,platform_code,zone_id,wheelchair_boarding,quality_flags,raw_row_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",[(sid,stop_id,*(clean(row.get(k)) for k in FIELDS),json.dumps(flags(row,idset),separators=(",",":")),json.dumps(row,sort_keys=True,separators=(",",":"))) for stop_id,row in zip(ids,stops)])
   after=conn.execute("SELECT COUNT(*) FROM gtfs_stop_structure WHERE snapshot_id=?",(sid,)).fetchone()[0]
  return {"snapshot_id":sid,"sha256":digest,"rows":after,"inserted":after-before}
 finally: conn.close()
def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("feed_zip",type=Path);p.add_argument("--feed-id",required=True);p.add_argument("--source-url");p.add_argument("--db",type=Path,default=DEFAULT_DB);a=p.parse_args(argv);print(json.dumps(import_stop_structure(a.db,a.feed_zip,a.feed_id,a.source_url),indent=2))
if __name__=="__main__": main()
