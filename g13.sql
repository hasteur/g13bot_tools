create table g13_records ( id auto_increment primary_key, article text, editor text, notified timestamp default current_timestamp, nominated timestamp default null);
create unique index g13_notify on g13_records (article,editor);
