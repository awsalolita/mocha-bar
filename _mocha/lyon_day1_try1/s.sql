create table if not exists DataProcessingAPP(
    id serial primary key,
    message varchar(255),
    process boolean
);
