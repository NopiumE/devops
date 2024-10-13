FROM postgres:15.6

RUN apt-get update && apt-get install -y gettext-base

COPY ./init.sql /docker-entrypoint-initdb.d/init.sql.raw

RUN mkdir -p /etc/postgresql/ /oracle/pg_data/archive/ /var/log/postgresql/ && \
    chown postgres:postgres /oracle/pg_data/archive/ /var/log/postgresql/

ENTRYPOINT [ "bash", "-c", "\
chown postgres:postgres /var/log/postgresql/ && \
envsubst < /docker-entrypoint-initdb.d/init.sql.raw > /docker-entrypoint-initdb.d/init.sql && \
cat <<EOF > /etc/postgresql/postgresql.conf \n\
listen_addresses = '*' \n\
port = ${DB_PORT} \n\
log_destination = 'stderr' \n\
logging_collector = on \n\
log_directory = '/var/log/postgresql/' \n\
log_filename = 'postgresql.log' \n\
archive_mode = on \n\
archive_command = 'cp %p /oracle/pg_data/archive/%f' \n\
max_wal_senders = 10 \n\
wal_level = replica \n\
wal_log_hints = on \n\
log_replication_commands = on \n\
EOF\n\
cat <<EOF > /etc/postgresql/pg_hba.conf \n\
local all ${POSTGRES_USER} peer \n\
host all all 0.0.0.0/0 password \n\
host replication ${DB_REPL_USER} 172.28.0.4/24 trust \n\
EOF\n\
docker-entrypoint.sh $@" ]

CMD ["postgres", "-c", "config_file=/etc/postgresql/postgresql.conf", "-c", "hba_file=/etc/postgresql/pg_hba.conf"]
