use bit;

select Host,User,plugin,authentication_string FROM mysql.user;

CREATE USER 'root'@'220.90.180.91' IDENTIFIED BY '1234';

drop table if exists memfaceimg;

create table memfaceimg
(
UserID varchar(50) not null,
UsName varchar(50) not null,
UsFace longtext not null,
foreign key (UserID) references member(UserID) on update cascade on delete cascade
);

desc memfaceimg;

select * from memfaceimg;

insert into memfaceimg values('', '', '');

select UsFace from memfaceimg where UserID = '';

delete from memfaceimg where UserID = 'wjddmlcks';

Drop table if exists member;

create table member
(
UserID varchar(50) not null primary key,
UserPW varchar(50) not null,
UsPhone varchar(50) not null,
UsName varchar(50) not null
);

DESC member;

delete from member where UserID = 'ww';

update member set ;

insert into member value('a', 'a', 'a', 'n');

select UserNo from member where UserID = 'a' and UserPW = 'b';

select exists (select * from member where UserID = '' and UserPW = '') as success;

select exists (select * from member where UserID = 'rlawndud') as success;

select * from member;

drop table if exists Images;

#진짜용
create table Images
(
Image_No int auto_increment primary key,
UserID varchar(50) not null,
image_data longtext not null,
teamNo int not null,
pre_face varchar(500),
pre_backgroud varchar(50),
pre_caption varchar(500),
latitude double,
longitude double,
location varchar(100),
img_date varchar(100),
season varchar(50),
foreign key (UserID) references member(UserID) on update cascade,
foreign key (teamNo) references team(teamNo) on update cascade on Delete cascade
);

insert into Images values(null, '', ?, '', ?, '', '');

select * from Images;

delete from Images where image_No = 70;

delete from Images where teamNo = 12;

select * from Images where UserID = '';

select * from Images where UserID = '' and Image_No > ?;

select * from Images where teamNo = ? or teamNo = ? or teamNo = ? and Image_No > ?;

select * from Images where teamNo = ? and Image_No > ?;

insert into Images values(null, '', '');

update Images set latitude = 35.10055161724439, longitude = 129.03257432952793, img_date = '2024/04/09 14:56:02', location = '부산광역시 중구 광복동2가', season = '봄' where Image_No = 7 or Image_No = 8;

drop table if exists friendcontrol;

create table friendcontrol(
from_mem_id varchar(50) not null,
to_mem_id varchar(50) not null,
is_friend bool not null,
foreign key (from_mem_id) references member(UserID) on update cascade on Delete cascade,
foreign key (to_mem_id) references member(UserID) on update cascade on Delete cascade
);

desc friendcontrol;

select * from friendcontrol;

select distinct fc1.to_mem_id, m.usname from friendcontrol fc1 join friendcontrol fc2 on fc1.to_mem_id = fc2.from_mem_id join member m on fc1.to_mem_id = m.userid where fc1.from_mem_id = 'z' and fc1.is_friend = true and fc2.is_friend = true;


insert into friendcontrol values('wooyung', 'rlawndud', true);
insert into friendcontrol values('rlawndud', 'wooyung', False);

insert into friendcontrol (from_mem_id, to_mem_id, is_friend) select '', '', true where '' != '' and not exists (select 1 from friendcontrol where from_mem_id = '' and to_mem_id = '' and is_friend = true);

select * from friendcontrol;

select fc.to_mem_id, m.UsName from friendcontrol fc join member m on fc.to_mem_id = m.UserID where fc.from_mem_id = 'z' and fc.is_friend = false;

update friendcontrol set is_friend = true where from_mem_id = 'wooyung' and to_mem_id = '3';

delete from friendcontrol where from_mem_id = 'dnjsgh0987' and to_mem_id = 'dnjsgh0987' and is_friend = false;

select fc1.to_mem_id from friendcontrol fc1 join friendcontrol fc2 on fc1.to_mem_id = fc2.from_mem_id where fc1.from_mem_id = 'a' and fc1.is_friend = true and fc2.is_friend = true;

drop table if exists team;

create table team(
teamNo int auto_increment primary key,
teamName varchar(50) not null,
LeaderID varchar(50) not null,
foreign key(LeaderID) references member(UserID) on update cascade
);

desc team;

select * from team;

insert into team values(25, '이거로테스트하시오행님', '1');

insert into team (teamNo, teamName, LeaderID) select null, 'YalRU', 'a' where not exists (select teamNo from team where LeaderID = 'a' and teamName = 'YalRU');

delete from team where LeaderID = '1';

delete from team where teamNo = 4;

select teamNo from team where LeaderID = '' and teamName = '';

select teamName from team where teamNo = '';

drop table if exists teammem;

create table teammem(
teamNo int not null,
teamName varchar(50) not null,
UserID varchar(50) not null,
isaccept bool not null,
foreign key (teamNo) references team(teamNo) on update cascade,
foreign key (UserID) references member(UserID) on update cascade
);

desc teammem;

insert into teammem values(25, '이거로테스트하시오행님', '1', True);

insert into teammem (teamNo, teamName, UserID, isaccept) select 5, 'YalRU', 'a', false where not exists (select 1 from teammem where teamNo = 5 and teamName = 'YalRU' and UserID = 'a' and isaccept = false);

select * from teammem;

select teamNo, teamName, UserID from teammem where isaccept = False;

select teamNo, teamName from teammem where UserID = 'rlawndud' and isaccept = true;

select tm.UserID, m.UsName from teammem tm join member m on m.UserID = tm.UserID where tm.teamNo = 1 and tm.teamName = 'aa' and isaccept = true;

select tm.UserID, m.UsName from teammem tm join member m on m.UserID = tm.UserID where tm.teamNo = 25 and isaccept = true;

select tm.UserID from teammem tm join member m on m.UserID = tm.UserID where teamNo = 5 and isaccept = true;

select count(*) from teammem where teamNo = 5; 

select * from teammem where isaccept = false;

delete from teammem where teamNo = 4;	

DELETE FROM teammem WHERE teamNo IN (SELECT teamNo FROM team WHERE LeaderID = '1');

delete from teammem where teamNo = 12 and UserID = 'q';

update teammem set isaccept = true where teamNo = 6 and teamName = 'YalRU' and UserID = 'rlawndud';