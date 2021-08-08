CREATE TABLE `project` (
  `name` varchar(255) NOT NULL,
  `source` varchar(511) NOT NULL,
  PRIMARY KEY (`name`)
);

CREATE TABLE `snippet` (
  `project_name` varchar(255) NOT NULL,
  `project_version` varchar(55) NOT NULL,
  `guava_version` varchar(55) NOT NULL,
  `snippet_file` varchar(255) NOT NULL,
  PRIMARY KEY (`project_name`,`project_version`),
  CONSTRAINT `name` FOREIGN KEY (`project_name`) REFERENCES `project` (`name`)
);

-- Using `hash_path` in key instead of `real_path` because of max key length limit
CREATE TABLE `file` (
  `project_name` varchar(255) NOT NULL,
  `project_version` varchar(55) NOT NULL,
  `real_path` varchar(511) NOT NULL,
  `hash_path` varchar(255) NOT NULL,
  PRIMARY KEY (`project_name`,`project_version`, `hash_path`),
  CONSTRAINT `project_name` FOREIGN KEY (`project_name`) REFERENCES `project` (`name`)
);
