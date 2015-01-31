create table interested_notify ( 
    id bigint not null auto_increment, 
    article varchar(255), 
    notified varchar(255), 
    PRIMARY KEY (id)
);
create index int_not on interested_notify (notified);
