CREATE TABLE `update_helper`.`snippet` (
  `snippet_id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `source` VARCHAR(511) NOT NULL,
  `project_version` VARCHAR(55) NOT NULL,
  `guava_version` VARCHAR(55) NOT NULL,
  `snippet_file` VARCHAR(255) NOT NULL,
  UNIQUE KEY (`source`, `project_version`),
  PRIMARY KEY (`snippet_id`)
);

CREATE TABLE `update_helper`.`file` (
  `file_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `real_path` VARCHAR(511) NOT NULL,
  `hash_path` VARCHAR(255) NOT NULL,
  UNIQUE KEY (`real_path`),
  PRIMARY KEY (`file_id`)
);

CREATE TABLE `update_helper`.`file_usage` (
  `snippet_id` INT UNSIGNED NOT NULL,
  `file_id` BIGINT UNSIGNED NOT NULL,
  PRIMARY KEY (`snippet_id`, `file_id`),
  CONSTRAINT `snippet_id`
    FOREIGN KEY (`snippet_id`)
    REFERENCES `update_helper`.`snippet` (`snippet_id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT `file_id`
    FOREIGN KEY (`file_id`)
    REFERENCES `update_helper`.`file` (`file_id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE
);
