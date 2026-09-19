-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Generation Time: Nov 30, 2025 at 06:48 PM
-- Server version: 10.4.32-MariaDB
-- PHP Version: 8.0.30

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `gtnhs smart quiz new db`
--

-- --------------------------------------------------------

--
-- Table structure for table `question_answers`
--

CREATE TABLE `question_answers` (
  `answer_id` int(11) NOT NULL,
  `question_id` int(11) NOT NULL,
  `correct_answer` text NOT NULL,
  `answer_format` enum('exact','contains','range') DEFAULT 'exact'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `question_answers`
--

INSERT INTO `question_answers` (`answer_id`, `question_id`, `correct_answer`, `answer_format`) VALUES
(34, 34, 'TRUE', 'exact'),
(35, 35, 'TRUE', 'exact'),
(36, 36, 'FALSE', 'exact'),
(37, 37, 'TRUE', 'exact'),
(38, 38, 'TRUE', 'exact'),
(39, 39, '23', 'exact'),
(40, 40, '17', 'exact'),
(41, 41, '18', 'exact'),
(42, 42, '12', 'exact'),
(43, 43, '12', 'exact'),
(44, 44, '10', 'exact'),
(45, 45, '3 × 3 × 5', 'exact'),
(46, 46, '20 square units', 'exact'),
(47, 47, 'TRUE', 'exact'),
(48, 48, 'FALSE', 'exact'),
(49, 49, 'TRUE', 'exact'),
(50, 50, 'TRUE', 'exact'),
(51, 51, 'TRUE', 'exact'),
(52, 52, '<ol>', 'exact'),
(53, 53, 'href', 'exact'),
(54, 54, '<img>', 'exact'),
(55, 55, 'Defines a division or section', 'exact'),
(56, 56, '<table>', 'exact'),
(57, 57, '<!-- This is a comment -->', 'exact'),
(58, 58, '<link rel=\"stylesheet\" type=\"text/css\" href=\"styles.css\">', 'exact'),
(59, 59, 'about the HTML document', 'exact'),
(60, 60, '<form>', 'exact'),
(61, 61, 'You use the <ul> tag ', 'exact'),
(62, 62, 'TRUE', 'exact'),
(63, 63, '3', 'exact');

-- --------------------------------------------------------

--
-- Table structure for table `question_choices`
--

CREATE TABLE `question_choices` (
  `choice_id` int(11) NOT NULL,
  `question_id` int(11) NOT NULL,
  `choice_text` varchar(500) NOT NULL,
  `is_correct` tinyint(1) DEFAULT 0,
  `choice_order` int(11) DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `question_choices`
--

INSERT INTO `question_choices` (`choice_id`, `question_id`, `choice_text`, `is_correct`, `choice_order`) VALUES
(45, 39, '23', 1, 1),
(46, 39, '43', 0, 2),
(47, 39, '4', 0, 3),
(48, 39, '4', 0, 4),
(49, 40, '17', 1, 1),
(50, 40, '3', 0, 2),
(51, 40, '32', 0, 3),
(52, 40, '21', 0, 4),
(53, 41, '43', 0, 1),
(54, 41, '32', 0, 2),
(55, 41, '18', 1, 3),
(56, 41, '32', 0, 4),
(57, 52, '<ol>', 1, 1),
(58, 52, '<ul>', 0, 2),
(59, 52, '<li>', 0, 3),
(60, 52, '<list>', 0, 4),
(61, 53, 'src', 0, 1),
(62, 53, 'href', 1, 2),
(63, 53, 'alt', 0, 3),
(64, 53, 'target', 0, 4),
(65, 54, '<src>', 0, 1),
(66, 54, '<image>', 0, 2),
(67, 54, '<img>', 1, 3),
(68, 54, '<picture>', 0, 4),
(69, 55, 'Creates a table', 0, 1),
(70, 55, 'Defines a division or section', 1, 2),
(71, 55, 'Makes text bold', 0, 3),
(72, 55, 'Defines a list item', 0, 4),
(73, 56, '<table>', 1, 1),
(74, 56, '<td>', 0, 2),
(75, 56, '<tr>', 0, 3),
(76, 56, '<thead>', 0, 4);

-- --------------------------------------------------------

--
-- Table structure for table `quizzes`
--

CREATE TABLE `quizzes` (
  `quiz_id` int(11) NOT NULL,
  `quiz_code` varchar(20) NOT NULL,
  `quiz_title` varchar(255) NOT NULL,
  `subject_id` int(11) NOT NULL,
  `section_id` int(11) NOT NULL,
  `topic` varchar(200) NOT NULL,
  `instructions` text DEFAULT NULL,
  `duration_minutes` int(11) NOT NULL,
  `total_points` int(11) DEFAULT 0,
  `created_by` int(11) NOT NULL,
  `quiz_status` enum('draft','scheduled','active','paused','completed','archived') DEFAULT 'draft',
  `is_deleted` tinyint(1) DEFAULT 0,
  `created_at` datetime DEFAULT current_timestamp(),
  `updated_at` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `deleted_at` datetime DEFAULT NULL,
  `scheduled_start` datetime DEFAULT NULL,
  `scheduled_end` datetime DEFAULT NULL,
  `archived_at` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `quizzes`
--

INSERT INTO `quizzes` (`quiz_id`, `quiz_code`, `quiz_title`, `subject_id`, `section_id`, `topic`, `instructions`, `duration_minutes`, `total_points`, `created_by`, `quiz_status`, `is_deleted`, `created_at`, `updated_at`, `deleted_at`, `scheduled_start`, `scheduled_end`, `archived_at`) VALUES
(11, 'Y06ZTFQ1', 'math - Math1', 10, 11, 'Math1', NULL, 20, 13, 1, 'draft', 0, '2025-12-01 01:31:48', '2025-12-01 01:31:48', NULL, NULL, NULL, NULL),
(12, 'X7QBD921', 'Programming - Introduction to html', 11, 12, 'Introduction to html', NULL, 30, 15, 1, 'draft', 0, '2025-12-01 01:39:07', '2025-12-01 01:39:07', NULL, NULL, NULL, NULL),
(13, '033XLLO6', 'math - math1', 10, 13, 'math1', NULL, 20, 2, 1, 'draft', 0, '2025-12-01 01:42:09', '2025-12-01 01:42:09', NULL, NULL, NULL, NULL);

-- --------------------------------------------------------

--
-- Table structure for table `quiz_analytics`
--

CREATE TABLE `quiz_analytics` (
  `analytics_id` int(11) NOT NULL,
  `quiz_id` int(11) NOT NULL,
  `total_attempts` int(11) DEFAULT 0,
  `average_score` decimal(5,2) DEFAULT 0.00,
  `completion_rate` decimal(5,2) DEFAULT 0.00,
  `average_time_taken` int(11) DEFAULT 0,
  `difficulty_analysis` text DEFAULT NULL,
  `last_updated` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `quiz_questions`
--

CREATE TABLE `quiz_questions` (
  `question_id` int(11) NOT NULL,
  `quiz_id` int(11) NOT NULL,
  `question_type` enum('true_false','multiple_choice','short_answer','essay') NOT NULL,
  `difficulty_level` enum('easy','medium','hard') NOT NULL,
  `question_text` text NOT NULL,
  `question_order` int(11) DEFAULT 0,
  `points` int(11) DEFAULT 1,
  `time_limit` int(11) DEFAULT NULL COMMENT 'Seconds per question',
  `explanation` text DEFAULT NULL,
  `image_url` varchar(255) DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `quiz_questions`
--

INSERT INTO `quiz_questions` (`question_id`, `quiz_id`, `question_type`, `difficulty_level`, `question_text`, `question_order`, `points`, `time_limit`, `explanation`, `image_url`, `created_at`) VALUES
(34, 11, 'true_false', 'easy', '5 + 3 = 8', 1, 1, NULL, NULL, NULL, '2025-12-01 01:31:48'),
(35, 11, 'true_false', 'easy', '10 is an even number.', 2, 1, NULL, NULL, NULL, '2025-12-01 01:31:48'),
(36, 11, 'true_false', 'easy', '4 × 2 = 7', 3, 1, NULL, NULL, NULL, '2025-12-01 01:31:48'),
(37, 11, 'true_false', 'easy', '12 is a multiple of 3.', 4, 1, NULL, NULL, NULL, '2025-12-01 01:31:48'),
(38, 11, 'true_false', 'easy', '15 ÷ 3 = 5', 5, 1, NULL, NULL, NULL, '2025-12-01 01:31:48'),
(39, 11, 'multiple_choice', 'medium', 'What is the value of 9 + 5 × 2?', 6, 1, NULL, NULL, NULL, '2025-12-01 01:31:48'),
(40, 11, 'multiple_choice', 'medium', 'If x = 7, what is the value of 2x + 3?', 7, 1, NULL, NULL, NULL, '2025-12-01 01:31:48'),
(41, 11, 'multiple_choice', 'medium', 'Which of the following is a multiple of 6?', 8, 1, NULL, NULL, NULL, '2025-12-01 01:31:48'),
(42, 11, 'short_answer', 'hard', 'Identify the greatest common divisor (GCD) of 24 and 36.', 9, 1, NULL, NULL, NULL, '2025-12-01 01:31:48'),
(43, 11, 'short_answer', 'hard', 'What is the least common multiple (LCM) of 4 and 6?', 10, 1, NULL, NULL, NULL, '2025-12-01 01:31:48'),
(44, 11, 'short_answer', 'hard', 'Identify the solution to the equation 2x - 5 = 15.', 11, 1, NULL, NULL, NULL, '2025-12-01 01:31:48'),
(45, 11, 'short_answer', 'hard', 'What is the prime factorization of 45?', 12, 1, NULL, NULL, NULL, '2025-12-01 01:31:48'),
(46, 11, 'short_answer', 'hard', 'Identify the area of a triangle with a base of 8 units and a height of 5 units.', 13, 1, NULL, NULL, NULL, '2025-12-01 01:31:48'),
(47, 12, 'true_false', 'easy', 'the <body> tag is used to define the content of the webpage.', 1, 1, NULL, NULL, NULL, '2025-12-01 01:39:07'),
(48, 12, 'true_false', 'easy', 'tag is used to create the smallest heading.', 2, 1, NULL, NULL, NULL, '2025-12-01 01:39:07'),
(49, 12, 'true_false', 'easy', 'tag is used to create paragraphs in HTML.', 3, 1, NULL, NULL, NULL, '2025-12-01 01:39:07'),
(50, 12, 'true_false', 'easy', 'tag is self-closing and does not require an end tag.', 4, 1, NULL, NULL, NULL, '2025-12-01 01:39:07'),
(51, 12, 'true_false', 'easy', 'tag is used to create hyperlinks in HTML.', 5, 1, NULL, NULL, NULL, '2025-12-01 01:39:07'),
(52, 12, 'multiple_choice', 'medium', 'Which tag is used to create an ordered list in HTML?', 6, 1, NULL, NULL, NULL, '2025-12-01 01:39:07'),
(53, 12, 'multiple_choice', 'medium', 'What attribute is used to specify the destination of a link in the <a> tag?', 7, 1, NULL, NULL, NULL, '2025-12-01 01:39:07'),
(54, 12, 'multiple_choice', 'medium', 'Which HTML tag is used to display an image on a webpage?', 8, 1, NULL, NULL, NULL, '2025-12-01 01:39:07'),
(55, 12, 'multiple_choice', 'medium', 'What does the <div> tag do in HTML?', 9, 1, NULL, NULL, NULL, '2025-12-01 01:39:07'),
(56, 12, 'multiple_choice', 'medium', 'Which HTML tag is used to define a table?', 10, 1, NULL, NULL, NULL, '2025-12-01 01:39:07'),
(57, 12, 'short_answer', 'hard', 'Identify the correct syntax to add a comment in HTML.', 11, 1, NULL, NULL, NULL, '2025-12-01 01:39:07'),
(58, 12, 'short_answer', 'hard', 'What is the correct way to link a CSS file in an HTML document?', 12, 1, NULL, NULL, NULL, '2025-12-01 01:39:07'),
(59, 12, 'short_answer', 'hard', 'Identify the purpose of the <meta> tag in HTML.', 13, 1, NULL, NULL, NULL, '2025-12-01 01:39:07'),
(60, 12, 'short_answer', 'hard', 'What is the correct HTML element to specify a form for user input', 14, 1, NULL, NULL, NULL, '2025-12-01 01:39:07'),
(61, 12, 'short_answer', 'hard', 'How do you make a list of items inside a non-ordered (bulleted) list in HTML?', 15, 1, NULL, NULL, NULL, '2025-12-01 01:39:07'),
(62, 13, 'true_false', 'easy', '1+1 = 2?', 1, 1, NULL, NULL, NULL, '2025-12-01 01:42:09'),
(63, 13, 'short_answer', 'hard', '1+2 = ?', 2, 1, NULL, NULL, NULL, '2025-12-01 01:42:09');

-- --------------------------------------------------------

--
-- Table structure for table `quiz_sessions`
--

CREATE TABLE `quiz_sessions` (
  `session_id` int(11) NOT NULL,
  `quiz_id` int(11) NOT NULL,
  `session_code` varchar(10) NOT NULL,
  `started_by` int(11) NOT NULL,
  `started_at` datetime DEFAULT current_timestamp(),
  `ended_at` datetime DEFAULT NULL,
  `session_status` enum('scheduled','active','paused','ended','cancelled') DEFAULT 'scheduled',
  `participant_count` int(11) DEFAULT 0,
  `completed_count` int(11) DEFAULT 0,
  `average_score` decimal(5,2) DEFAULT 0.00
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `sections`
--

CREATE TABLE `sections` (
  `section_id` int(11) NOT NULL,
  `section_name` varchar(100) NOT NULL,
  `grade_level` int(11) NOT NULL,
  `adviser_id` int(11) DEFAULT NULL,
  `school_year` varchar(20) NOT NULL,
  `is_active` tinyint(1) DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `sections`
--

INSERT INTO `sections` (`section_id`, `section_name`, `grade_level`, `adviser_id`, `school_year`, `is_active`) VALUES
(2, 'fsfsd', 8, NULL, '2024-2025', 1),
(3, 'fsdaf', 8, NULL, '2024-2025', 1),
(4, 'fsdffsd', 8, NULL, '2024-2025', 1),
(5, 'fsdfsad', 8, NULL, '2024-2025', 1),
(6, 'fdsafds', 8, NULL, '2024-2025', 1),
(7, 'dsfgd', 8, NULL, '2024-2025', 1),
(8, 'fsafsd', 8, NULL, '2024-2025', 1),
(9, 'gdsgdsg', 9, NULL, '2024-2025', 1),
(10, 'sdfgdf', 8, NULL, '2024-2025', 1),
(11, 'Ict-7', 7, NULL, '2024-2025', 1),
(12, 'Ict-8', 8, NULL, '2024-2025', 1),
(13, 'testing', 7, NULL, '2024-2025', 1);

-- --------------------------------------------------------

--
-- Table structure for table `students`
--

CREATE TABLE `students` (
  `student_id` int(11) NOT NULL,
  `lrn` varchar(20) DEFAULT NULL,
  `first_name` varchar(100) DEFAULT NULL,
  `last_name` varchar(100) DEFAULT NULL,
  `grade_level` int(11) NOT NULL,
  `section` varchar(50) DEFAULT NULL,
  `parent_contact` varchar(20) DEFAULT NULL,
  `enrollment_status` enum('active','inactive','transferred','graduated') DEFAULT 'active'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `student_answers`
--

CREATE TABLE `student_answers` (
  `student_answer_id` int(11) NOT NULL,
  `attempt_id` int(11) NOT NULL,
  `question_id` int(11) NOT NULL,
  `answer_text` text DEFAULT NULL,
  `selected_choice_id` int(11) DEFAULT NULL,
  `is_correct` tinyint(1) DEFAULT 0,
  `points_earned` int(11) DEFAULT 0,
  `answered_at` datetime DEFAULT current_timestamp(),
  `time_spent_seconds` int(11) DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `student_quiz_attempts`
--

CREATE TABLE `student_quiz_attempts` (
  `attempt_id` int(11) NOT NULL,
  `quiz_id` int(11) NOT NULL,
  `student_id` int(11) NOT NULL,
  `session_id` int(11) DEFAULT NULL,
  `attempt_number` int(11) DEFAULT 1,
  `started_at` datetime DEFAULT current_timestamp(),
  `completed_at` datetime DEFAULT NULL,
  `time_taken_seconds` int(11) DEFAULT 0,
  `score` decimal(5,2) DEFAULT 0.00,
  `raw_score` int(11) DEFAULT 0,
  `total_points` int(11) DEFAULT 0,
  `attempt_status` enum('not_started','in_progress','completed','timed_out','submitted') DEFAULT 'not_started',
  `ip_address` varchar(45) DEFAULT NULL,
  `user_agent` text DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `subjects`
--

CREATE TABLE `subjects` (
  `subject_id` int(11) NOT NULL,
  `subject_code` varchar(20) NOT NULL,
  `subject_name` varchar(100) NOT NULL,
  `description` text DEFAULT NULL,
  `grade_level` int(11) DEFAULT NULL,
  `is_active` tinyint(1) DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `subjects`
--

INSERT INTO `subjects` (`subject_id`, `subject_code`, `subject_name`, `description`, `grade_level`, `is_active`) VALUES
(2, 'FDS', 'fds', NULL, NULL, 1),
(3, 'GFDG', 'gfdg', NULL, NULL, 1),
(4, 'DFSFSD', 'dfsfsd', NULL, NULL, 1),
(5, 'FSFS', 'fsfs', NULL, NULL, 1),
(6, 'FFSDAF', 'ffsdaf', NULL, NULL, 1),
(7, 'FSADF', 'fsadf', NULL, NULL, 1),
(8, 'GFD', 'gfd', NULL, NULL, 1),
(9, 'GDSFG', 'gdsfg', NULL, NULL, 1),
(10, 'MATH', 'math', NULL, NULL, 1),
(11, 'PROGRAMMIN', 'Programming', NULL, NULL, 1);

-- --------------------------------------------------------

--
-- Table structure for table `system_logs`
--

CREATE TABLE `system_logs` (
  `log_id` int(11) NOT NULL,
  `user_id` int(11) DEFAULT NULL,
  `action` varchar(100) NOT NULL,
  `description` text DEFAULT NULL,
  `ip_address` varchar(45) DEFAULT NULL,
  `user_agent` text DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `teachers`
--

CREATE TABLE `teachers` (
  `teacher_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `department` varchar(100) DEFAULT NULL,
  `employee_id` varchar(50) DEFAULT NULL,
  `subjects_handled` text DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `teachers`
--

INSERT INTO `teachers` (`teacher_id`, `user_id`, `department`, `employee_id`, `subjects_handled`) VALUES
(1, 0, 'General', 'T001', 'All Subjects');

--
-- Indexes for dumped tables
--

--
-- Indexes for table `question_answers`
--
ALTER TABLE `question_answers`
  ADD PRIMARY KEY (`answer_id`),
  ADD UNIQUE KEY `question_id` (`question_id`);

--
-- Indexes for table `question_choices`
--
ALTER TABLE `question_choices`
  ADD PRIMARY KEY (`choice_id`),
  ADD KEY `question_id` (`question_id`);

--
-- Indexes for table `quizzes`
--
ALTER TABLE `quizzes`
  ADD PRIMARY KEY (`quiz_id`),
  ADD UNIQUE KEY `quiz_code` (`quiz_code`),
  ADD KEY `idx_quiz_status` (`quiz_status`),
  ADD KEY `idx_quiz_deleted` (`is_deleted`),
  ADD KEY `subject_id` (`subject_id`),
  ADD KEY `section_id` (`section_id`),
  ADD KEY `created_by` (`created_by`);

--
-- Indexes for table `quiz_analytics`
--
ALTER TABLE `quiz_analytics`
  ADD PRIMARY KEY (`analytics_id`),
  ADD UNIQUE KEY `quiz_id` (`quiz_id`);

--
-- Indexes for table `quiz_questions`
--
ALTER TABLE `quiz_questions`
  ADD PRIMARY KEY (`question_id`),
  ADD KEY `idx_question_type` (`question_type`),
  ADD KEY `idx_difficulty` (`difficulty_level`),
  ADD KEY `quiz_id` (`quiz_id`);

--
-- Indexes for table `quiz_sessions`
--
ALTER TABLE `quiz_sessions`
  ADD PRIMARY KEY (`session_id`),
  ADD UNIQUE KEY `session_code` (`session_code`),
  ADD KEY `quiz_id` (`quiz_id`),
  ADD KEY `started_by` (`started_by`),
  ADD KEY `idx_session_status` (`session_status`);

--
-- Indexes for table `sections`
--
ALTER TABLE `sections`
  ADD PRIMARY KEY (`section_id`),
  ADD UNIQUE KEY `unique_section` (`section_name`,`grade_level`,`school_year`),
  ADD KEY `idx_section_active` (`is_active`),
  ADD KEY `adviser_id` (`adviser_id`);

--
-- Indexes for table `students`
--
ALTER TABLE `students`
  ADD PRIMARY KEY (`student_id`),
  ADD UNIQUE KEY `lrn` (`lrn`),
  ADD KEY `idx_grade_level` (`grade_level`),
  ADD KEY `idx_enrollment_status` (`enrollment_status`);

--
-- Indexes for table `student_answers`
--
ALTER TABLE `student_answers`
  ADD PRIMARY KEY (`student_answer_id`),
  ADD UNIQUE KEY `unique_student_answer` (`attempt_id`,`question_id`),
  ADD KEY `question_id` (`question_id`),
  ADD KEY `selected_choice_id` (`selected_choice_id`);

--
-- Indexes for table `student_quiz_attempts`
--
ALTER TABLE `student_quiz_attempts`
  ADD PRIMARY KEY (`attempt_id`),
  ADD UNIQUE KEY `unique_attempt` (`quiz_id`,`student_id`,`attempt_number`),
  ADD KEY `student_id` (`student_id`),
  ADD KEY `session_id` (`session_id`),
  ADD KEY `idx_attempt_status` (`attempt_status`);

--
-- Indexes for table `subjects`
--
ALTER TABLE `subjects`
  ADD PRIMARY KEY (`subject_id`),
  ADD UNIQUE KEY `subject_code` (`subject_code`),
  ADD KEY `idx_subject_active` (`is_active`);

--
-- Indexes for table `system_logs`
--
ALTER TABLE `system_logs`
  ADD PRIMARY KEY (`log_id`),
  ADD KEY `user_id` (`user_id`),
  ADD KEY `idx_action` (`action`),
  ADD KEY `idx_created_at` (`created_at`);

--
-- Indexes for table `teachers`
--
ALTER TABLE `teachers`
  ADD PRIMARY KEY (`teacher_id`),
  ADD UNIQUE KEY `user_id` (`user_id`),
  ADD UNIQUE KEY `employee_id` (`employee_id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `question_answers`
--
ALTER TABLE `question_answers`
  MODIFY `answer_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=64;

--
-- AUTO_INCREMENT for table `question_choices`
--
ALTER TABLE `question_choices`
  MODIFY `choice_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=77;

--
-- AUTO_INCREMENT for table `quizzes`
--
ALTER TABLE `quizzes`
  MODIFY `quiz_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=14;

--
-- AUTO_INCREMENT for table `quiz_analytics`
--
ALTER TABLE `quiz_analytics`
  MODIFY `analytics_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `quiz_questions`
--
ALTER TABLE `quiz_questions`
  MODIFY `question_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=64;

--
-- AUTO_INCREMENT for table `quiz_sessions`
--
ALTER TABLE `quiz_sessions`
  MODIFY `session_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=7;

--
-- AUTO_INCREMENT for table `sections`
--
ALTER TABLE `sections`
  MODIFY `section_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=14;

--
-- AUTO_INCREMENT for table `students`
--
ALTER TABLE `students`
  MODIFY `student_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=17;

--
-- AUTO_INCREMENT for table `student_answers`
--
ALTER TABLE `student_answers`
  MODIFY `student_answer_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=50;

--
-- AUTO_INCREMENT for table `student_quiz_attempts`
--
ALTER TABLE `student_quiz_attempts`
  MODIFY `attempt_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=15;

--
-- AUTO_INCREMENT for table `subjects`
--
ALTER TABLE `subjects`
  MODIFY `subject_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=12;

--
-- AUTO_INCREMENT for table `system_logs`
--
ALTER TABLE `system_logs`
  MODIFY `log_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `teachers`
--
ALTER TABLE `teachers`
  MODIFY `teacher_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=2;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `question_answers`
--
ALTER TABLE `question_answers`
  ADD CONSTRAINT `question_answers_ibfk_1` FOREIGN KEY (`question_id`) REFERENCES `quiz_questions` (`question_id`) ON DELETE CASCADE;

--
-- Constraints for table `question_choices`
--
ALTER TABLE `question_choices`
  ADD CONSTRAINT `question_choices_ibfk_1` FOREIGN KEY (`question_id`) REFERENCES `quiz_questions` (`question_id`) ON DELETE CASCADE;

--
-- Constraints for table `quizzes`
--
ALTER TABLE `quizzes`
  ADD CONSTRAINT `quizzes_ibfk_1` FOREIGN KEY (`subject_id`) REFERENCES `subjects` (`subject_id`),
  ADD CONSTRAINT `quizzes_ibfk_2` FOREIGN KEY (`section_id`) REFERENCES `sections` (`section_id`);

--
-- Constraints for table `quiz_analytics`
--
ALTER TABLE `quiz_analytics`
  ADD CONSTRAINT `quiz_analytics_ibfk_1` FOREIGN KEY (`quiz_id`) REFERENCES `quizzes` (`quiz_id`);

--
-- Constraints for table `quiz_questions`
--
ALTER TABLE `quiz_questions`
  ADD CONSTRAINT `quiz_questions_ibfk_1` FOREIGN KEY (`quiz_id`) REFERENCES `quizzes` (`quiz_id`) ON DELETE CASCADE;

--
-- Constraints for table `quiz_sessions`
--
ALTER TABLE `quiz_sessions`
  ADD CONSTRAINT `quiz_sessions_ibfk_1` FOREIGN KEY (`quiz_id`) REFERENCES `quizzes` (`quiz_id`),
  ADD CONSTRAINT `quiz_sessions_ibfk_2` FOREIGN KEY (`started_by`) REFERENCES `teachers` (`teacher_id`);

--
-- Constraints for table `sections`
--
ALTER TABLE `sections`
  ADD CONSTRAINT `sections_ibfk_1` FOREIGN KEY (`adviser_id`) REFERENCES `teachers` (`teacher_id`);

--
-- Constraints for table `student_answers`
--
ALTER TABLE `student_answers`
  ADD CONSTRAINT `student_answers_ibfk_1` FOREIGN KEY (`attempt_id`) REFERENCES `student_quiz_attempts` (`attempt_id`) ON DELETE CASCADE,
  ADD CONSTRAINT `student_answers_ibfk_2` FOREIGN KEY (`question_id`) REFERENCES `quiz_questions` (`question_id`),
  ADD CONSTRAINT `student_answers_ibfk_3` FOREIGN KEY (`selected_choice_id`) REFERENCES `question_choices` (`choice_id`);

--
-- Constraints for table `student_quiz_attempts`
--
ALTER TABLE `student_quiz_attempts`
  ADD CONSTRAINT `student_quiz_attempts_ibfk_1` FOREIGN KEY (`quiz_id`) REFERENCES `quizzes` (`quiz_id`),
  ADD CONSTRAINT `student_quiz_attempts_ibfk_2` FOREIGN KEY (`student_id`) REFERENCES `students` (`student_id`),
  ADD CONSTRAINT `student_quiz_attempts_ibfk_3` FOREIGN KEY (`session_id`) REFERENCES `quiz_sessions` (`session_id`);

--
-- Constraints for table `system_logs`
--
ALTER TABLE `system_logs`
  ADD CONSTRAINT `system_logs_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
