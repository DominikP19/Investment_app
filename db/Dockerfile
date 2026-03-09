FROM postgres:18
COPY 01_table_seed.sql /docker-entrypoint-initdb.d/
COPY 02_trigger_seed.sql /docker-entrypoint-initdb.d/