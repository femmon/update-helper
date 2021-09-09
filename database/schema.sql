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

CREATE TABLE `update_helper`.`job` (
  `job_id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `source` VARCHAR(511) NOT NULL,
  `commit` VARCHAR(55) NOT NULL,
  `source_guava_version` VARCHAR(55) NOT NULL,
  `target_guava_version` VARCHAR(55) NOT NULL,
  `job_snippet_file` VARCHAR(255),
  `job_status` INT UNSIGNED NOT NULL,
  CONSTRAINT `status`
    FOREIGN KEY (`job_status`)
    REFERENCES `update_helper`.`status` (`status_id`)
    ON DELETE RESTRICT
    ON UPDATE CASCADE,
  PRIMARY KEY (`job_id`)
);

CREATE TABLE `update_helper`.`job_file_usage` (
  `job_id` INT UNSIGNED NOT NULL,
  `file_id` BIGINT UNSIGNED NOT NULL,
  PRIMARY KEY (`job_id`, `file_id`),
  CONSTRAINT `job_id`
    FOREIGN KEY (`job_id`)
    REFERENCES `update_helper`.`job` (`job_id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT `job_file_usage_file_id`
    FOREIGN KEY (`file_id`)
    REFERENCES `update_helper`.`file` (`file_id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE
);

CREATE TABLE `update_helper`.`status` (
  `status_id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `label` VARCHAR(55) NOT NULL,
  UNIQUE KEY (`label`),
  PRIMARY KEY (`status_id`)
);

INSERT INTO `update_helper`.`status` (`label`) VALUES ('INITIALIZING'), ('RUNNING'), ('FINISHED'), ('QUEUEING'), ('ERROR');

CREATE TABLE `update_helper`.`job_component` (
  `job_component_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `job_id` INT UNSIGNED NOT NULL,
  `snippet_id` INT UNSIGNED NOT NULL,
  `job_component_status` INT UNSIGNED NOT NULL,
  CONSTRAINT `job_component_job_id`
    FOREIGN KEY (`job_id`)
    REFERENCES `update_helper`.`job` (`job_id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT `job_component_snippet_id`
    FOREIGN KEY (`snippet_id`)
    REFERENCES `update_helper`.`snippet` (`snippet_id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT `job_component_status`
    FOREIGN KEY (`job_component_status`)
    REFERENCES `update_helper`.`status` (`status_id`)
    ON DELETE RESTRICT
    ON UPDATE CASCADE,
  PRIMARY KEY (`job_component_id`)
);

CREATE TABLE `update_helper`.`job_result` (
  `job_result_id` BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `job_component_id` BIGINT UNSIGNED NOT NULL,
  `job_file_id` BIGINT UNSIGNED NOT NULL,
  `job_function` VARCHAR(31) NOT NULL,
  `snippet_file_id` BIGINT UNSIGNED NOT NULL,
  `snippet_function` VARCHAR(31) NOT NULL,
  CONSTRAINT `job_result_job_component_id`
    FOREIGN KEY (`job_component_id`)
    REFERENCES `update_helper`.`job_component` (`job_component_id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT `job_result_job_file_id`
    FOREIGN KEY (`job_file_id`)
    REFERENCES `update_helper`.`file` (`file_id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  CONSTRAINT `job_result_snippet_file_id`
    FOREIGN KEY (`snippet_file_id`)
    REFERENCES `update_helper`.`file` (`file_id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE,
  UNIQUE KEY (`job_component_id`, `job_file_id`, `job_function`, `snippet_file_id`, `snippet_function`),
  PRIMARY KEY (`job_result_id`)
);
