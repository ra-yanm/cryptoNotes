-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Generation Time: Sep 04, 2026 at 02:35 PM
-- Server version: 10.6.23-MariaDB
-- PHP Version: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `flaskdb447`
--
CREATE DATABASE IF NOT EXISTS `flaskdb447` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE `flaskdb447`;

-- --------------------------------------------------------

--
-- Table structure for table `account_otp`
--

DROP TABLE IF EXISTS `account_otp`;
CREATE TABLE `account_otp` (
  `challenge_id` char(64) NOT NULL,
  `user_ID` varchar(20) DEFAULT NULL,
  `email` varchar(254) NOT NULL,
  `purpose` varchar(20) NOT NULL,
  `otp_hash` char(64) NOT NULL,
  `payload` text DEFAULT NULL,
  `expires_at` datetime NOT NULL,
  `used_at` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `account_otp`
--

INSERT INTO `account_otp` (`challenge_id`, `user_ID`, `email`, `purpose`, `otp_hash`, `payload`, `expires_at`, `used_at`) VALUES
('1df65ac383905c9b4d1157d880f93edb8a3aef0968ab0f749fc7757b461962b4', '241411', 'rayanmokhtar@outlook.com', 'login', '05a74ad48b6e30e273245c25c7ba4648657d480f1b90c80e38e8e5c72bb0f306', NULL, '2026-09-04 12:03:39', '2026-09-04 11:59:25'),
('3b05df4f40da7da011c38f8979c2bc41304a7f9a4aa0113504d41fed46767993', '241411', 'rayanmokhtar@outlook.com', 'login', '8b405f4b882bb05ac07ae36eb85f4d34374a20a4138ea89d4927c8183f517089', NULL, '2026-09-04 11:52:11', '2026-09-04 11:47:39'),
('96f09b957b812b5f7386fb2d127da7478959b3dd0f68069e3c617a4d80a2112d', '241411', 'rayanmokhtar@outlook.com', 'login', 'bf47154693bec841ce95de551b34284daa265d7e345009f2c69cfc99aa3bc406', NULL, '2026-09-04 12:23:33', NULL),
('e1a3e66912d4e64b779cd2c0c5ac795dc9b10481d73d25b4222dc2829d4bd439', '241411', 'rayanmokhtar@outlook.com', 'login', 'f9298705bae8be3a10c00d3c45159153a8d013c8ee8aaf59704f6169beb16be0', NULL, '2026-09-04 12:23:34', '2026-09-04 12:18:51');

-- --------------------------------------------------------

--
-- Table structure for table `courses`
--

DROP TABLE IF EXISTS `courses`;
CREATE TABLE `courses` (
  `courseID` char(6) NOT NULL,
  `title` text DEFAULT NULL,
  `description` text DEFAULT NULL,
  `coordinator` varchar(20) NOT NULL DEFAULT 'teacher1'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `courses`
--

INSERT INTO `courses` (`courseID`, `title`, `description`, `coordinator`) VALUES
('CSE110', 'Programming Language I', 'This course introduces foundational knowledge of string manipulation, arrays, control structure, file input/output, and the like. The debugging techniques and programming tools will make the students well-equipped in creating fundamental programs. From the anticipated outcomes of this course students will be able to: 1. Use flow control design tools, create flowcharts for solving problems. Write, debug, and execute programs using a programming language from hands-on experience. 2. Apply branching and looping structures to control program flow, and implement conditional statements, loops, and basic programming concepts to solve simple problems. Also, manipulate text data using string manipulation techniques. 3. Create, read, and modify arrays to store and process data, and sort array items using various sorting techniques.', 'teacher1'),
('CSE111', 'Programming Language II', 'This course would be an introduction to data structures, formal specification, and syntax of Object Oriented Programming (OOP), elements of language theory, and mathematical preliminaries. Other topics that would be covered are formal languages, structured programming concepts, and a survey of the features of existing high-level languages. Students would design and write applications using an appropriate language. The course includes a compulsory 3-hour laboratory work each week.', 'teacher2'),
('CSE220', 'Data Structure', 'This course is an introduction to data structures, where the students will study the elementary data structures such as arrays, lists, stacks, queues, trees, etc. These data structures will be used to study and implement different algorithms such as sorting, searching, tree traversal, etc. The course includes a 3 hour mandatory laboratory per week as CSE220L. In the laboratory, the students will use a standard programming language, usually Java, to implement the various data structures and algorithms learned in the theory component of the course.', 'teacher1'),
('CSE221', 'Algorithm Analysis & Design', 'This course addresses the study of efficient algorithms, their analyses and effective algorithm design techniques. Standard algorithm design strategies, such as, Divide and Conquer paradigm, Greedy method, Dynamic programming, Backtracking, Basic search and traversal techniques, Graph algorithms, Elementary parallel algorithms, Algebraic simplification and transformations, Lower bound theory, NP-hard and NP-complete problems are discussed in the course. Examples of data structures and algorithms studied in details are Heaps; Hashing; Graph algorithms: Shortest paths, Depth-first and Breadth-first search, Network flow, Computational geometry, Minimum Spanning Tree; Integer arithmetic: GCD, primality; polynomial and matrix calculations; Sorting; Performance bounds, asymptotic analysis, worst case and average case behavior, correctness and complexity. The course includes a compulsory 3 hour laboratory work every week.', 'teacher1'),
('CSE331', 'Automata and Computability', 'Alphabets, strings, and languages, Deterministic Finite Automata (DFA), Regular Languages, the Regular Operations, Regular Language closure properties, Nondeterminism, Nondeterministic Finite Automata (NFA), Equivalence between DFA and NFA using Subset Construction, Regular Expressions, Equivalence between Regular Expressions and Finite Automata, Converting Regular Expressions to NFA, Converting DFA into Regular Expressions using the State Elimination Method, Nonregular Languages, Pumping Lemma for Regular Languages, Context-Free Grammars (CFG) and Context-Free Languages (CFL), Parse Trees, Derivations, and Ambiguity, Chomsky Normal Form (CNF), the Cocke-Younger-Kasami (CYK) algorithm, Pushdown Automata (PDA) and its equivalence with CFGs, Turing Machines (TM), Turing-Recognizable and Turing-Decidable Languages, TM Variants, Undecidability, the Halting Problem, Reducibility.', 'teacher3'),
('CSE370', 'Database', 'This course is designed as an introduction to relational database management systems (RDBMS) focusing on the efficient design, implementation and optimization of an RDBMS. Topics covered will include the advantages and disadvantages of DBMS, database architecture, data modeling using ER and EER models, relational integrity constraints, relational schema mapping from ER/EER, indexing, hashing and normalization. SQL Query formulation will be extensively practiced in both the theoretical and laboratory components of the course. The course includes a compulsory 3 hour laboratory work each week as CSE370L. Students must complete several hands-on SQL assignments and a group project for the laboratory work. The group project will involve the design and implementation of a complete database system including a user interface.', 'teacher3'),
('MAT216', 'Linear Algebra and Fourier Ana', 'This course is designed to provide the learners with a solid understanding of the concepts of Linear Algebra, an indispensable part of both the fields of Computer Science and Mathematics. This is an undergraduate course for students of Engineering, Science, and Mathematics. Linear algebra is the study of linear systems of equations, vector spaces, and linear transformations. Solving systems of linear equations is a basic tool of many mathematical procedures used for solving problems in science and engineering.', 'teacher1'),
('PHY111', 'Principles of Physics I', 'This is designed to introduce the principles of Newtonian mechanics at the freshmen level of the undergraduate study for engineering majors or equivalent. The key concepts to be developed throughout the semester are: vectors, equations of motions, Newton’s laws, conservation laws of energy, momentum, the work- energy theorem, extension of linear motion to rotational motion including the conservation laws, gravitation, elasticity and their properties, SHM.', 'teacher4');

-- --------------------------------------------------------

--
-- Table structure for table `notes`
--

DROP TABLE IF EXISTS `notes`;
CREATE TABLE `notes` (
  `courseID` char(6) NOT NULL,
  `noteID` int(11) NOT NULL,
  `title` text DEFAULT NULL,
  `note` text DEFAULT NULL,
  `student_view` tinyint(1) NOT NULL DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `notes`
--

INSERT INTO `notes` (`courseID`, `noteID`, `title`, `note`, `student_view`) VALUES
('CSE221', 7, 'Introduction to Algorithms', 'Informally, an algorithm is any well-defined computational procedure that takes some value, or set of values, as input and produces some value, or set of values, as output in a finite amount of time. An algorithm is thus a sequence of computational steps that transform the input into the output. \r\nAn algorithm for a computational problem is correct if every problem instance provided as input halts or finishes its computing in finite time and outputs the correct solution to the problem instance.\r\n\r\nThere are two main criteria for judging the merits of algorithms:\r\n \r\nCorrectness (does the algorithm solve the problem in a finite number of steps?) \r\nEfficiency (how much resources in terms of memory and time does it take to execute?)\r\n\r\nDefinition: A finite set of statements that guarantees an optimal solution in a finite interval of time.\r\n', 1),
('CSE370', 23, 'The Mini World', 'The mini world concept is essential in ER modeling. It helps in\r\nidentifying and defining the relevant entities and relationships\r\nrequired for database design.\r\n\r\nMini world is some part of the real world about which data is\r\nstored in a database. For example, if we want to create a\r\ndatabase for train reservation in Bangladesh, then the train\r\nreservation system is the mini-world. Similarly, if we want to\r\ncreate a database for a university, then that University is the\r\nmini-world that we will represent in our database.\r\n\r\nNote, the mini-world is not shown on the ER diagram.', 1),
('CSE370', 24, 'Entities and Entity Types', 'Entities are specific objects or things in the mini-world that are\r\nrepresented in the database.\r\n\r\nFor example, the STUDENT Sakib Chowdhury, the CSE\r\nDEPARTMENT or the course CSE370 are all entities in the\r\nUniversity mini-world. Thus, if there are 5000 students enrolled in\r\nthe university, then they are all 5000 individual entities.\r\n\r\nAll these 5000 students have similar type of information stored\r\nabout them and they have the same role within the mini-world, so\r\nthey can be grouped together into the Student entity type. So,\r\nwhen several entities are grouped together due to sharing the\r\nsame properties and role then it is called the Entity Type.\r\n\r\nEntity types are shown in ER diagram using a \"rectangle\" shape.', 1),
('CSE370', 25, 'Attributes (1)', 'Attributes are properties used to describe an entity. For example,\r\na STUDENT may have attributes such as id, name, cgpa, email,\r\netc. A specific entity will have a value for each of its attributes.\r\nThere are 3 types of Attributes:\r\n\r\nSimple: Each entity has a single atomic value for the attribute.\r\nFor example, STUDENT id, cgpa, EMPLOYEE salary. It is shown\r\nusing an \"oval\" shape in the ER diagram.\r\n\r\nMultivalued: An entity may have multiple values for that attribute.\r\nFor example, color of a CAR or email of a STUDENT. It is shown\r\nusing a \"double oval\" shape in the ER.\r\n\r\nComposite: Each value of the attribute is composed of several\r\ncomponents. For example, Address(Apt#, House#, Street, City,\r\nState, ZipCode, Country), or Name(FirstName MiddleName\r\nLastName). Some components may themselves be composite.\r\n\"Ovals\" are connected to other \"ovals\" in the ER.\r\n\r\nAn attribute can be composite-multivalued, for example, previous\r\ndegrees of a STUDENT.', 1),
('CSE370', 26, 'Attributes (2)', 'Key Attribute\r\nAn attribute of an entity type for which each entity must have a\r\nunique value is called a key attribute of the entity type. For\r\nexample, Student ID or email, Course code.\r\n\r\nKey attributes are \"underlined\" in the ER diagram. An entity\r\ncan have more than one key attribute. A key attribute should not\r\nbe multivalued.\r\n\r\nDerived Attribute\r\nAn attribute value that can be calculated/derived from other\r\nstored data, it is called a derived attribute. It means the value will\r\nnot be stored in the database, but instead will be derived when\r\nneeded in order to save space.\r\n\r\nFor example, \"total bill\" of an ORDER when the unit price and\r\nquantity is stored, \"age\" of a STUDENT when birthdate is stored.\r\nDerived attribute is shown using a \"dotted oval\" in ER diagram.', 0),
('CSE370', 27, 'Weak Entity', 'Sometimes an entity may not have any unique (key) attributes.\r\nIn such cases the individual entities cannot be uniquely\r\nidentified using its own attributes. Such entities belong to weak\r\nentity types. The example of SECTIONS in a university mini-\r\nworld (on the left) illustrates a weak entity type.\r\n\r\nWeak entity types are shown using a \"double rectangle\" in the\r\nER diagram and such an entity type must not have any key\r\nattributes.\r\n\r\nPartial Key\r\nA weak entity may not have a key attribute, but it may have an\r\nattribute that is \"part\" of a unique key/value. Such an attribute is\r\ncalled a partial key and is shown using a \"dotted underline\".\r\nOn the left Section Number is not unique as many sections (of\r\ndifferent courses) will have the same number. But the section\r\nnumber is part of the key that will be used to identify a particular\r\nsection.', 1),
('CSE370', 28, 'Relationships', 'A relationship relates two or more distinct entities with a\r\nspecific meaning. For example, EMPLOYEE John Smith works\r\non the ProductX PROJECT, or STUDENT Ahnaf Atef enrolls in\r\nthe CSE370 COURSE. Relationships of the same type are\r\ngrouped together into a relationship type.\r\n\r\nRelationship types are shown using a \"diamond\" shape\r\nconnected to the related entity types.\r\n\r\nRelationship types may or may not have attributes. In the\r\nexample, \"grade\" is a relationship attribute because unless a\r\nSTUDENT enrolls in a particular COURSE, there will be no grade for\r\nthat student. Thus, the grade value will only exist if a relationship is\r\nestablished between a specific student and a specific course.\r\n\r\nThe same entity types may have different relationships between\r\nthem, each relationship type conveying different meanings. For\r\nexample, STUDENT and COURSE have two different relationship\r\ntypes: \"enrolls_in\" and \"ST_of\".', 1);

-- --------------------------------------------------------

--
-- Table structure for table `note_messages`
--

DROP TABLE IF EXISTS `note_messages`;
CREATE TABLE `note_messages` (
  `message_id` bigint(20) NOT NULL,
  `noteID` int(11) NOT NULL,
  `student_ID` varchar(20) NOT NULL,
  `faculty_ID` varchar(20) NOT NULL,
  `sender_ID` varchar(20) NOT NULL,
  `ciphertext_for_student` text NOT NULL,
  `ciphertext_for_faculty` text NOT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `note_messages`
--

INSERT INTO `note_messages` (`message_id`, `noteID`, `student_ID`, `faculty_ID`, `sender_ID`, `ciphertext_for_student`, `ciphertext_for_faculty`, `created_at`) VALUES
(1, 23, '241411', 'teacher3', '241411', '{\"ephemeral\":[17918651363320087255422444189363140564164914066140474443380149529645011619362,88353956444995388022187665545267843802223568736239302666677227011892521752799],\"nonce\":\"f03c6d8d267b3eae73e2f87d99f9f9e0\",\"data\":\"49aa\",\"tag\":\"348b0b5fe82f1de07bfaf313d87cbe68326529aaf4854b93d79084b60dd67b0e\"}', '{\"ephemeral\":[71030799517268992936360011971181764906586939822375375702704519043706056121308,15223788926847796123584100164690945130938668367383545341427115889924539546636],\"nonce\":\"6dcbd8e8891a0660fbbec0d4164b7f06\",\"data\":\"10a4\",\"tag\":\"565d885c02a5178fa7b3b637414d8236070b06e55617fd59b638a06cabacbef5\"}', '2026-09-04 15:40:04'),
(2, 23, '241411', 'teacher3', '241411', '{\"ephemeral\":[78935742597224982825782875744976085511275961996684123582669914839143515799230,37187625946259787222760192332025455078775416615319965992311745927557199686298],\"nonce\":\"971a69eccbf718e09c051bff891f4ee3\",\"data\":\"02a48753e2\",\"tag\":\"4b7de031f85e1a03c8cb9ea76c4c7354f35722e526165af2a137370a604f0c98\"}', '{\"ephemeral\":[69909513120046975044727283379501105682198582325300500302575499839829158549919,36459677397463715906336223502342380772554953039435149161167659295600295462021],\"nonce\":\"725f3f3cac4f37c8ef9acb940cebc6b7\",\"data\":\"92e05137da\",\"tag\":\"a211ef6c49e3877d2e7040adfd6322f58416a3397efa5f8eb06a591b109313e7\"}', '2026-09-04 18:07:29');

-- --------------------------------------------------------

--
-- Table structure for table `note_pending`
--

DROP TABLE IF EXISTS `note_pending`;
CREATE TABLE `note_pending` (
  `ID` int(11) NOT NULL,
  `courseID` varchar(6) NOT NULL,
  `title` text DEFAULT NULL,
  `note` text DEFAULT NULL,
  `post_by` varchar(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `note_pending`
--

INSERT INTO `note_pending` (`ID`, `courseID`, `title`, `note`, `post_by`) VALUES
(8, 'CSE331', 'wqerfgh', 'wfegrhtyhujk', 'st1'),
(25, 'CSE370', 'Relationship Constraints (1)', 'Cardinality Ratio (specifies maximum participation):\r\n\r\nShown in the ER by placing appropriate numbers on the\r\nrelationship edges:\r\n\r\nOne-to-one (1:1): A single entity in one entity type is\r\nrelated to a single entity in the other entity type. E.g. 1\r\nFACULTY member can coordinate only 1 COURSE at a\r\ntime and a COURSE will have only 1 COORDINATOR.\r\n\r\nOne-to-many (1:N) or Many-to-one (N:1): An entity\r\nfrom one type can be related to multiple entities from\r\nthe other entity type, or vice versa. 1 COURSE has many\r\nSECTIONs, but a SECTION belongs to only 1 COURSE.\r\n\r\nMany-to-many (M:N): Multiple entities from one type\r\nare related to multiple entities from the other type. Many\r\nSTUDENTS are enrolled in a SECTION, and a SECTION\r\nhas many STUDENTS in it.\r\nrelationship.\r\n\r\nA relationship of degree n is called an n-ary\r\nrelatiosnhip, meaning \"n\" number of entity types are\r\nparticipating in that relationship.', '24141104'),
(30, 'CSE221', 'fwdswcw', 'ewfrtyuioiuiyuhtrgrfsd', 'student1'),
(31, 'CSE221', '{\"ephemeral\":[26424977358788454894445036255626546507887910422508199682471841779384814156895,999504092095767969910193755888526759734189224845509904988000442059760463253],\"nonce\":\"9bdee41588d19166dfc641e562f663d5\",\"data\":\"c4efcea1cb\",\"tag\":\"2a0015e4ae6a7aba5683e8be98c60731c678220596d75c012c2538bd079372b1\"}', '{\"ephemeral\":[37623063899653053450086198385430510281126635551381267790745354372608682900606,63299544354856735154955259364205802776509922715435045235871925126588975922716],\"nonce\":\"ce33bc126c1674303ad1c7a3513aeca7\",\"data\":\"b65dfa4c4a394c4db2432b610e72845b915af30b91b56fd33624d3cd7db9811c51d0a9b0451fbdf57ac61f3a821fc2bf2ed9eb906f55f62dc3ca7e159f3cf81107e231009c07a47fb5e4a2333a2ced50\",\"tag\":\"b95daf6a3d1586d3137afbd7a150d86a968dc27add40408ef6f86fff3f7491d8\"}', '241411');

-- --------------------------------------------------------

--
-- Table structure for table `note_suggestions`
--

DROP TABLE IF EXISTS `note_suggestions`;
CREATE TABLE `note_suggestions` (
  `courseID` char(6) NOT NULL,
  `noteID` int(11) NOT NULL,
  `suggestionID` int(11) NOT NULL,
  `suggestion` text DEFAULT NULL,
  `suggested_by` varchar(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `note_suggestions`
--

INSERT INTO `note_suggestions` (`courseID`, `noteID`, `suggestionID`, `suggestion`, `suggested_by`) VALUES
('CSE370', 23, 35, 'efgrhtyghj,yjtrhtjThe mini world concept is essential in ER modeling. It helps in\r\nidentifying and defining the relevant entities and relationships\r\nrequired for database design.\r\n\r\nMini world is some part of the real world about which data is\r\nstored in a database. For example, ifewtyrtul', '24141104'),
('CSE370', 27, 36, 'Sometimes an entity may not have any unique (key) attributes.\r\nIn such cases the individual entities cannot be uniquely\r\nidentified using its own attributes. Such entities belong to weak\r\nentity types. The example of SECTIONS in a university mini-\r\nworld (on the left) illustrates a weak entity type.\r\n\r\nWeak entity types are shown using a \"double rectangle\" in the\r\nER diagram and such an entity type must not have any key\r\nattributes (but may have partial key attribute).\r\n\r\nPartial Key\r\nA weak entity may not have a key attribute, but it may have an\r\nattribute that is \"part\" of a unique key/value. Such an attribute is\r\ncalled a partial key and is shown using a \"dotted underline\".\r\nOn the left Section Number is not unique as many sections (of\r\ndifferent courses) will have the same number. But the section\r\nnumber is part of the key that will be used to identify a particular\r\nsection.', '24141104'),
('CSE221', 7, 41, 'Informally, an algorithm is any well-defined computational procedure that takes some value, or set of values, as input and produces some value, or set of values, as output in a finite amount of time. An algorithm is thus a sequence of computational steps that transform the input into the output. \r\nAn algorithm for a computational problem is correct if every problem instance provided as input halts or finishes its computing in finite time and outputs the correct solution to the problem instance.\r\n\r\nThere are two main criteria for judging the merits of algorithms:\r\n \r\nCorrectness (does the algorithm solve the problem in a finite number of steps?) \r\nEfficiency (how much resources in terms of memory and time does it take to execute?)\r\n\r\nDefinition: A finite set of statements that guarantees an optimal solution in a finite interval of time.\r\n\r\nNew suggestion\r\n', '24141104'),
('CSE370', 25, 42, 'Attributes are properties used to describe an entity. For example,\r\na STUDENT may have attributes such as id, name, cgpa, email,\r\netc. A specific entity will have a value for each of its attributes.\r\nThere are 3 types of Attributes:\r\n\r\nSimple: Each entity has a single atomic value for the attribute.\r\nFor example, STUDENT id, cgpa, EMPLOYEE salary. It is shown\r\nusing an \"oval\" shape in gewgewgER diagram.\r\n\r\nMultivalued: An entity may have multiple values for that attribute.\r\nFor example, color of a CAR or email of a STUDENT. It is shown\r\nusing a \"double oval\" shape in the ER.\r\n\r\nComposite: Each value of the attribute is composed of several\r\ncomponents. For example, Address(Apt#, House#, Street, City,\r\nState, ZipCode, Country), or Name(FirstName MiddleName\r\nLastName). Some components may themselves be composite.\r\n\"Ovals\" are connected to other \"ovals\" in the ER.\r\n\r\nAn attribute can be composite-multivalued, for example, previous\r\ndegrees of a STUDENT.', '24141104');

-- --------------------------------------------------------

-- Legacy table retained only so old dump rows can be imported before cleanup.
DROP TABLE IF EXISTS `secure_login`;
CREATE TABLE `secure_login` (
  `identity_hash` char(64) NOT NULL,
  `encrypted_credentials` text NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

INSERT INTO `secure_login` (`identity_hash`, `encrypted_credentials`) VALUES
('80efae7e9c31dad933076634c12eb07eeed74d320191910e925f11ac5d87e1af', '{\"version\":2,\"blocks\":[1420785621928518371880090746470115905464757173287851877083447047666843508981464471617330545553854628265966924032021627179332192407311648086895236347256461,4262677179294481050633606534900571924743792965196571579320282439373609557965732025472946716894740942957213665342852189800576274500979685230994943742216400],\"lengths\":[63,62],\"tag\":\"addd3e97a85c137d2a5393f46c7a6d45dd77cc292ee9b07917b427b47515b12e\"}'),
('f30aaae83fc4a70c69fd8605f0a7281d8603b872aa057e29e123f5d665f075d1', '{\"version\":2,\"blocks\":[3911872832009341617472802895375413618178096673143542915820574586141712482222383252472487995408597333652856656127092119254066057587937256661784203348943715,4632998427397271816355141200757856049207152682800194656123094319470995258923968918137797908284491994130361219608132824127284536457108590825958020061102387],\"lengths\":[63,44],\"tag\":\"8f8cd20beb821cc9bdeb3866288450700be174a85d3e867edf3193328a9c6172\"}');

-- --------------------------------------------------------

--
-- Table structure for table `user`
--

DROP TABLE IF EXISTS `user`;
CREATE TABLE `user` (
  `user_ID` varchar(20) NOT NULL,
  `email` varchar(254) DEFAULT NULL,
  `password` text DEFAULT NULL,
  `name` text NOT NULL,
  `department` text NOT NULL,
  `user_type` varchar(10) NOT NULL,
  `bio` text DEFAULT NULL,
  `personal_phn` text DEFAULT NULL,
  `discord_id` text DEFAULT NULL,
  `email_verified` tinyint(1) NOT NULL DEFAULT 1,
  `created_at` datetime NOT NULL DEFAULT current_timestamp()
) ;

CREATE TABLE `admins` (
  `admin_ID` varchar(20) NOT NULL,
  `email` varchar(254) NOT NULL,
  `password` text NOT NULL,
  `name` varchar(100) NOT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`admin_ID`),
  UNIQUE KEY `admins_email_unique` (`email`)
) ;

--
-- Dumping data for table `user`
--

INSERT INTO `user` (`user_ID`, `email`, `password`, `name`, `department`, `user_type`, `bio`, `personal_phn`, `discord_id`, `email_verified`) VALUES
('24101664', 'ramisa@bracu.com', 'passwords', 'Ramisa Ridhi', 'CSE', 'student', 'Computer science student interested in software development.', '01700000001', 'ramisa_24101664', 1),
('24101667', 'arannita@bracu.com', 'passwords', 'arannita', 'CSE', 'student', 'CSE student and technology enthusiast.', '01700000002', 'arannita_24101667', 1),
('241411', 'rayanmokhtar@outlook.com', '$2b$12$2RKCnmeg/umAiqZlOcEIaO.tSqCXE.YeZjaicGrXtCA.Q9u4ogh..', 'Rayan', 'CSE', 'student', '{\"ephemeral\":[18678203949923654312703651865478684761966571236402566215720591412973745580060,53362918119549727064460091049263238750838966171377657812623276376646228268722],\"nonce\":\"e90045f9ddb9fd8d623aa3a77db1c616\",\"data\":\"8f7cc79a219b541ba37d3a\",\"tag\":\"a4482910062c724cc365c3eb30532a5ae2a7e152f8ab549b4e366a2a7c239f2d\"}', '01552222222', '{\"ephemeral\":[3896275828310896134095540601072934108996696639073701608551523591847613771080,45947756440494333304589572153868288869932311720342541360118166056167399766778],\"nonce\":\"9f642d5cf6bcd5784aa809faecfd20b4\",\"data\":\"9bd7f42ceacf9f3c5a\",\"tag\":\"ae0598c6734b1cc6bb63af935c499c3c021054829eed81b2783a0cdaba747ce2\"}', 1),
('24141104', 'rayan@bracu.bd', 'passwords', 'Rayan', 'CS', 'student', 'Student interested in databases and web applications.', '01700000003', 'rayan_24141104', 1),
('st1', 'st@email.com', 'passwords', 'Mr. St', 'CSE', 'st', 'Student tutor and academic support volunteer.', '01700000004', 'mrst_st1', 1),
('student1', 'student1@email.com', 'pass', 'Siam', 'MNS', 'student', 'Student interested in collaborative learning.', '01000000000', 'siamDDC', 1),
('teacher1', 'teacher@email.com', 'passwords', 'Mr. Teacher', 'CSE', 'faculty', 'Faculty member coordinating undergraduate computer science courses.', '01700000006', 'mrteacher_faculty', 1),
('teacher2', 'teacher2@email.com', 'passwords', 'Dr. Anika Rahman', 'CSE', 'faculty', NULL, NULL, NULL, 1),
('teacher3', 'teacher3@email.com', 'passwords', 'Dr. Farhan Ahmed', 'CSE', 'faculty', NULL, NULL, NULL, 1),
('teacher4', 'teacher4@email.com', 'passwords', 'Ms. Nusrat Karim', 'CSE', 'faculty', NULL, NULL, NULL, 1);

-- --------------------------------------------------------

--
-- Table structure for table `user_ecc_keys`
--

DROP TABLE IF EXISTS `user_ecc_keys`;
CREATE TABLE `user_ecc_keys` (
  `user_ID` varchar(20) NOT NULL,
  `public_key` text NOT NULL,
  `encrypted_private_key` text NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `user_ecc_keys`
--

INSERT INTO `user_ecc_keys` (`user_ID`, `public_key`, `encrypted_private_key`) VALUES
('241411', '[105097532714411806004539561201784487857093657033216459852601619167599367807629, 82795850494816836295030867958014952764057020805395171250462634926281347874832]', '{\"ephemeral\":[52479981964328042767742278678005664161626379228257868093227466967868465960746,104864792731820735433226049164581733840394761198006373557216985496029493413198],\"nonce\":\"75df04bfa9f1ac14b6e41e6e59777aac\",\"data\":\"de612239ed788d33279aeccdd3f09fcbb63aaeea823a5bc0d633a7ff3db49757422ba6abc0fa8e98dae8f93f0de9d796f8717ec90de02bdc182c37dd8605977d20cb32692cf72f784956cffc33\",\"tag\":\"d39434fccee1510e82dbb0c9d577adb86a0c8d147f631bc2b17e86382d08f1f3\"}'),
('teacher3', '[76974386252258213803445062672483067681707436761725639574563296091739806927716, 14901669207238569571749247354771405726631577619634578984226102793735683421947]', '{\"ephemeral\":[108024258384300230440353120357900556782329359166046430052011743195577284710677,112047008951781782753053963118913349371708059919561303353475832338534315620690],\"nonce\":\"aa507ec6533cc09a0fbcd39e78b2a961\",\"data\":\"e66bcd36c4a40c003b1b461954d4c2b6965bb9610b04e979dc7cf0708110d466f16b76e7e69dd403b52d9559b7183c23e1836767d371a0bd4a86a22b97ba1d46c19da0b36d1e8f9fe1074b136f\",\"tag\":\"b6745d68e851e306f7948e0fa91bf0da08d550b0c4fe993a0da340b878205c5a\"}');

--
-- Indexes for dumped tables
--

--
-- Indexes for table `account_otp`
--
ALTER TABLE `account_otp`
  ADD PRIMARY KEY (`challenge_id`),
  ADD KEY `account_otp_user` (`user_ID`);

--
-- Indexes for table `courses`
--
ALTER TABLE `courses`
  ADD PRIMARY KEY (`courseID`),
  ADD KEY `coordinator` (`coordinator`);

--
-- Indexes for table `notes`
--
ALTER TABLE `notes`
  ADD PRIMARY KEY (`noteID`),
  ADD KEY `courseID` (`courseID`);

--
-- Indexes for table `note_messages`
--
ALTER TABLE `note_messages`
  ADD PRIMARY KEY (`message_id`),
  ADD KEY `note_message_lookup` (`noteID`,`student_ID`,`created_at`);

--
-- Indexes for table `note_pending`
--
ALTER TABLE `note_pending`
  ADD PRIMARY KEY (`ID`),
  ADD KEY `fk_course` (`courseID`),
  ADD KEY `fk_user` (`post_by`);

--
-- Indexes for table `note_suggestions`
--
ALTER TABLE `note_suggestions`
  ADD PRIMARY KEY (`suggestionID`),
  ADD KEY `fk_suggested_by` (`suggested_by`),
  ADD KEY `fk_lectureID` (`noteID`);

--
-- Indexes for table `secure_login`
--
ALTER TABLE `secure_login`
  ADD PRIMARY KEY (`identity_hash`);

--
-- Indexes for table `user`
--
ALTER TABLE `user`
  ADD PRIMARY KEY (`user_ID`),
  ADD UNIQUE KEY `email` (`email`);

--
-- Indexes for table `user_ecc_keys`
--
ALTER TABLE `user_ecc_keys`
  ADD PRIMARY KEY (`user_ID`);

--
-- Constraints for current application-owned security tables
--
ALTER TABLE `account_otp`
  ADD CONSTRAINT `account_otp_user_fk` FOREIGN KEY (`user_ID`) REFERENCES `user` (`user_ID`) ON DELETE SET NULL ON UPDATE CASCADE;

ALTER TABLE `user_ecc_keys`
  ADD CONSTRAINT `user_ecc_keys_user_fk` FOREIGN KEY (`user_ID`) REFERENCES `user` (`user_ID`) ON DELETE CASCADE ON UPDATE CASCADE;

ALTER TABLE `note_messages`
  ADD CONSTRAINT `note_messages_note_fk` FOREIGN KEY (`noteID`) REFERENCES `notes` (`noteID`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `note_messages_student_fk` FOREIGN KEY (`student_ID`) REFERENCES `user` (`user_ID`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `note_messages_faculty_fk` FOREIGN KEY (`faculty_ID`) REFERENCES `user` (`user_ID`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `note_messages_sender_fk` FOREIGN KEY (`sender_ID`) REFERENCES `user` (`user_ID`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `notes`
--
ALTER TABLE `notes`
  MODIFY `noteID` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=33;

--
-- AUTO_INCREMENT for table `note_messages`
--
ALTER TABLE `note_messages`
  MODIFY `message_id` bigint(20) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT for table `note_pending`
--
ALTER TABLE `note_pending`
  MODIFY `ID` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=32;

--
-- AUTO_INCREMENT for table `note_suggestions`
--
ALTER TABLE `note_suggestions`
  MODIFY `suggestionID` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=43;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `courses`
--
ALTER TABLE `courses`
  ADD CONSTRAINT `courses_coordinator_fk` FOREIGN KEY (`coordinator`) REFERENCES `user` (`user_ID`) ON DELETE NO ACTION ON UPDATE CASCADE;

--
-- Constraints for table `notes`
--
ALTER TABLE `notes`
  ADD CONSTRAINT `fk_notes_course` FOREIGN KEY (`courseID`) REFERENCES `courses` (`courseID`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `note_pending`
--
ALTER TABLE `note_pending`
  ADD CONSTRAINT `fk_course` FOREIGN KEY (`courseID`) REFERENCES `courses` (`courseID`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_user` FOREIGN KEY (`post_by`) REFERENCES `user` (`user_ID`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `note_suggestions`
--
ALTER TABLE `note_suggestions`
  ADD CONSTRAINT `fk_lectureID` FOREIGN KEY (`noteID`) REFERENCES `notes` (`noteID`) ON DELETE CASCADE ON UPDATE CASCADE,
  ADD CONSTRAINT `fk_suggested_by` FOREIGN KEY (`suggested_by`) REFERENCES `user` (`user_ID`) ON DELETE CASCADE ON UPDATE CASCADE;

DROP TABLE IF EXISTS `secure_login`;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
