import ibis
import ibis.expr.datatypes as dt
from ibis.backends.sql.datatypes import PostgresType

pt = PostgresType.from_string("point")
print("PostgresType.from_string('point') =", pt)
print("is_geospatial =", pt.is_geospatial(), "| is_unknown =", pt.is_unknown())

# native pg `point` column: must NOT be wrapped in ST_AsEWKB
schema = ibis.schema({"id": "int32", "user_point": pt})
t = ibis.table(schema, name="demo")
print("\n--- native point: t.select(...) ---")
print(ibis.to_sql(t.select("id", "user_point"), dialect="postgres"))

print("--- native point: filter ---")
print(ibis.to_sql(t.filter(t.id > 1), dialect="postgres"))

# postgis geometry column: must STILL be wrapped in ST_AsEWKB
geo = ibis.table(ibis.schema({"id": "int32", "g": dt.point}), name="geo_demo")
print("\n--- postgis geometry (must keep ST_AsEWKB) ---")
print(ibis.to_sql(geo, dialect="postgres"))

# DDL round-trip: creating a table with a point column should emit POINT
print("--- DDL (create table) ---")
print(ibis.to_sql(ibis.memtable([], schema=schema), dialect="postgres") if False else "")
from ibis.backends.sql.compilers.postgres import compiler as pg_compiler

print(pg_compiler.type_mapper.from_ibis(pt).sql("postgres"))
