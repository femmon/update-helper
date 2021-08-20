CREATE TABLE `update_helper`.`snippet` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `source` VARCHAR(511) NOT NULL,
  `project_version` VARCHAR(55) NOT NULL,
  `guava_version` VARCHAR(55) NOT NULL,
  `snippet_file` VARCHAR(255) NOT NULL,
  UNIQUE KEY (`source`, `project_version`),
  PRIMARY KEY (`id`)
);

CREATE TABLE `update_helper`.`file` (
  `snippet_id` INT UNSIGNED NOT NULL,
  `real_path` VARCHAR(511) NOT NULL,
  `hash_path` VARCHAR(255) NOT NULL,
  PRIMARY KEY (`snippet_id`, `real_path`),
  CONSTRAINT `id`
    FOREIGN KEY (`snippet_id`)
    REFERENCES `update_helper`.`snippet` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE
);
