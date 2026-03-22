-- --------------------------------------------------------
-- 主机:                           127.0.0.1
-- 服务器版本:                        10.6.22-MariaDB - mariadb.org binary distribution
-- 服务器操作系统:                      Win64
-- HeidiSQL 版本:                  12.10.0.7000
-- --------------------------------------------------------

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET NAMES utf8 */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;


-- 导出 aihmc_auth 的数据库结构
DROP DATABASE IF EXISTS `aihmc_auth`;
CREATE DATABASE IF NOT EXISTS `aihmc_auth` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci */;
USE `aihmc_auth`;

-- 导出  表 aihmc_auth.figura 结构
DROP TABLE IF EXISTS `figura`;
CREATE TABLE IF NOT EXISTS `figura` (
  `uuid` varchar(32) DEFAULT NULL,
  `username` varchar(16) DEFAULT NULL,
  UNIQUE KEY `uuid` (`uuid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 正在导出表  aihmc_auth.figura 的数据：~0 rows (大约)
DELETE FROM `figura`;

-- 导出  表 aihmc_auth.namelink 结构
DROP TABLE IF EXISTS `namelink`;
CREATE TABLE IF NOT EXISTS `namelink` (
  `uuid` varchar(32) DEFAULT NULL,
  `username` varchar(32) DEFAULT NULL,
  UNIQUE KEY `uuid` (`uuid`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 正在导出表  aihmc_auth.namelink 的数据：~0 rows (大约)
DELETE FROM `namelink`;

-- 导出  表 aihmc_auth.offline 结构
DROP TABLE IF EXISTS `offline`;
CREATE TABLE IF NOT EXISTS `offline` (
  `username` varchar(50) DEFAULT NULL,
  `uuid` varchar(50) DEFAULT NULL,
  `password` varchar(255) DEFAULT NULL,
  `ip` varchar(50) DEFAULT NULL,
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 正在导出表  aihmc_auth.offline 的数据：~0 rows (大约)
DELETE FROM `offline`;

-- 导出  表 aihmc_auth.skins 结构
DROP TABLE IF EXISTS `skins`;
CREATE TABLE IF NOT EXISTS `skins` (
  `username` varchar(16) DEFAULT NULL,
  `cape_hash` longtext DEFAULT NULL,
  `skin_hash` longtext DEFAULT NULL,
  `model_type` varchar(32) DEFAULT NULL,
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 正在导出表  aihmc_auth.skins 的数据：~0 rows (大约)
DELETE FROM `skins`;

-- 导出  表 aihmc_auth.userlink 结构
DROP TABLE IF EXISTS `userlink`;
CREATE TABLE IF NOT EXISTS `userlink` (
  `uuid` varchar(32) DEFAULT NULL,
  `new_uuid` varchar(32) DEFAULT NULL,
  UNIQUE KEY `uuid` (`uuid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 正在导出表  aihmc_auth.userlink 的数据：~0 rows (大约)
DELETE FROM `userlink`;

-- 导出  表 aihmc_auth.users 结构
DROP TABLE IF EXISTS `users`;
CREATE TABLE IF NOT EXISTS `users` (
  `uuid` varchar(32) DEFAULT NULL,
  `username` varchar(32) DEFAULT NULL,
  `last_source` varchar(32) DEFAULT NULL,
  `last_ip` varchar(32) DEFAULT NULL,
  `textures_value` longtext DEFAULT NULL,
  `textures_signature` longtext DEFAULT NULL,
  UNIQUE KEY `uuid` (`uuid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 正在导出表  aihmc_auth.users 的数据：~0 rows (大约)
DELETE FROM `users`;

/*!40103 SET TIME_ZONE=IFNULL(@OLD_TIME_ZONE, 'system') */;
/*!40101 SET SQL_MODE=IFNULL(@OLD_SQL_MODE, '') */;
/*!40014 SET FOREIGN_KEY_CHECKS=IFNULL(@OLD_FOREIGN_KEY_CHECKS, 1) */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40111 SET SQL_NOTES=IFNULL(@OLD_SQL_NOTES, 1) */;
