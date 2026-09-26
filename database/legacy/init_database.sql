-- Create userservice database
CREATE DATABASE IF NOT EXISTS userservice DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE userservice;

-- Create class table first because user references it.
CREATE TABLE IF NOT EXISTS `class` (
    class_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    class_name VARCHAR(255) NOT NULL,
    class_detail TEXT,
    admin_id INT,
    is_end INT DEFAULT 0,
    UNIQUE KEY uk_class_name (class_name)
);

-- Create user table used by the real login and registration flow.
CREATE TABLE IF NOT EXISTS `user` (
    user_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_student_number VARCHAR(13) NOT NULL,
    user_password VARCHAR(255) NOT NULL,
    user_tel VARCHAR(11),
    user_image VARCHAR(255),
    user_name VARCHAR(255),
    user_academy VARCHAR(255),
    user_email VARCHAR(255),
    user_gender INT DEFAULT 2,
    class_id_class_id BIGINT NOT NULL,
    is_admin BOOLEAN DEFAULT FALSE,
    is_deleted INT DEFAULT 0,
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_user_student_number (user_student_number),
    KEY idx_user_class_id (class_id_class_id),
    CONSTRAINT fk_user_class
        FOREIGN KEY (class_id_class_id) REFERENCES `class`(class_id)
);

-- Seed a default class and admin account for initial deployment.
INSERT IGNORE INTO `class` (class_name, class_detail) VALUES
('网络安全232班', '用户服务默认班级'),
('网络安全231班', '网络安全231班'),
('网络安全233班', '网络安全233班');

INSERT IGNORE INTO `user` (user_student_number, user_password, user_name, user_gender, class_id_class_id, is_admin) VALUES
('admin', 'e10adc3949ba59abbe56e057f20f883e', 'Administrator', 1, 1, true); -- password: 123456 (legacy MD5)

-- Create experimentmoduleservice database
CREATE DATABASE IF NOT EXISTS experimentmoduleservice DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE experimentmoduleservice;

-- Create course table
CREATE TABLE IF NOT EXISTS `course` (
    id INT AUTO_INCREMENT PRIMARY KEY,
    course_name VARCHAR(255) NOT NULL,
    course_description TEXT,
    difficulty INT,
    type VARCHAR(50),
    tags JSON,
    image_url VARCHAR(255),
    cost_time INT,
    schedule VARCHAR(255),
    course_status INT DEFAULT 1,
    instructor VARCHAR(255)
);

-- Create module table
CREATE TABLE IF NOT EXISTS `module` (
    id INT AUTO_INCREMENT PRIMARY KEY,
    module_name VARCHAR(255) NOT NULL,
    introduction TEXT,
    difficulty INT,
    image_id INT,
    type JSON,
    task_points JSON
);

-- Create module_course relation table
CREATE TABLE IF NOT EXISTS `module_course` (
    module_id INT,
    course_id INT,
    PRIMARY KEY (module_id, course_id)
);

-- Insert existing course data
INSERT INTO experimentmoduleservice.course (cost_time, course_description, difficulty, image_url, instructor, course_name, schedule, course_status, tags, `type`) VALUES
(8,'娣卞害瑙ｆ瀽瀛楃鍨?鏁板€煎瀷娉ㄥ叆鍘熺悊锛屾兜鐩栬仈鍚堟煡璇㈡敞鍏ャ€佸竷灏旂洸娉ㄣ€佹椂闂寸洸娉ㄣ€佹姤閿欐敞鍏ョ瓑6澶ф敾鍑荤被鍨嬶紝瀹為獙鍖呭惈绌烘牸缁曡繃銆丠EX缂栫爜缁曡繃銆佹敞閲婄杩囨护绐佺牬绛?绉嶉槻寰＄粫杩囨妧鏈?,3,'a9fe8e50-ba21-45ef-abd5-50b717857502-1.SQL娉ㄥ叆鏀婚槻瀹炴垬.png','寮犳槬鍗?,'SQL娉ㄥ叆鏀婚槻瀹炴垬','姣忓懆涓€',1,'["SQL娉ㄥ叆", "Web瀹夊叏"]','web'),
(6,'鏋勫缓鍙嶅皠鍨媂SS閽撻奔椤甸潰銆佸瓨鍌ㄥ瀷XSS鎸佷箙鍖栨敾鍑汇€丏OM鍨媂SS鍓嶇婕忔礊鍒╃敤涓夊ぇ瀹為獙鍦烘櫙锛屽疄鎴樻紨绀篊ookie绐冨彇銆佷細璇濆姭鎸併€丅eEF妗嗘灦鍗忓悓鏀诲嚮',2,'eb678908-4878-4303-94ae-b3434d52612a-2.XSS婕忔礊娣卞害瑙ｆ瀽.png','鏉庢槑杞?,'XSS婕忔礊娣卞害瑙ｆ瀽','姣忓懆浜?,1,'["XSS", "Web瀹夊叏"]','web'),
(7,'浠庡鎴风鏍￠獙缁曡繃鍒版湇鍔＄妫€娴嬬獊鐮达紝娑电洊鍥剧墖椹埗浣溿€丆ontent-Type浼€犮€?htaccess鏀诲嚮銆佷簩娆℃覆鏌撳鎶椼€佺珵浜夋潯浠朵笂浼犵瓑鍏ㄩ摼鏉℃敾鍑绘墜娉?,3,'5780e906-42a1-4a88-ad06-d054bbf92735-3.鏂囦欢涓婁紶婕忔礊绐佺牬.png','鐜嬩紵鍥?,'鏂囦欢涓婁紶婕忔礊绐佺牬','姣忓懆涓€',1,'["鏂囦欢涓婁紶", "Web瀹夊叏"]','web');

-- Insert existing module data
INSERT INTO experimentmoduleservice.module (difficulty, image_id, introduction, module_name, task_points, `type`) VALUES
(2, 101, '缃戠粶瀹夊叏鍩虹鍏ラ棬璇剧▼', '缃戠粶瀹夊叏鍩虹', '[]', '["鐞嗚","鍩虹"]'),
(3, 102, 'Web瀹夊叏婕忔礊瀹炴垬婕旂粌', 'Web瀹夊叏鏀婚槻', '[]', '["瀹炴垬","鏀婚槻"]');

-- Create relations between modules and courses
INSERT INTO experimentmoduleservice.module_course (module_id, course_id) VALUES
(2, 1),
(2, 2),
(2, 3);

-- Create imagedb database (used to store image metadata)
CREATE DATABASE IF NOT EXISTS imagedb DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE imagedb;

-- Create images table
CREATE TABLE IF NOT EXISTS `images` (
    id INT AUTO_INCREMENT PRIMARY KEY,
    content_type VARCHAR(50),
    filename VARCHAR(255),
    original_filename VARCHAR(255),
    path VARCHAR(255),
    size BIGINT,
    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    url VARCHAR(255)
);

-- Insert some image metadata
INSERT INTO imagedb.images (content_type, filename, original_filename, path, size, upload_time, url) VALUES
('image/png', 'a9fe8e50-ba21-45ef-abd5-50b717857502-1.SQL娉ㄥ叆鏀婚槻瀹炴垬.png', '1.SQL娉ㄥ叆鏀婚槻瀹炴垬.png', 'upload-dir/a9fe8e50-ba21-45ef-abd5-50b717857502-1.SQL娉ㄥ叆鏀婚槻瀹炴垬.png', 302733, '2025-04-03 20:33:33.236599', '/api/images/view/a9fe8e50-ba21-45ef-abd5-50b717857502-1.SQL娉ㄥ叆鏀婚槻瀹炴垬.png'),
('image/png', 'eb678908-4878-4303-94ae-b3434d52612a-2.XSS婕忔礊娣卞害瑙ｆ瀽.png', '2.XSS婕忔礊娣卞害瑙ｆ瀽.png', 'upload-dir/eb678908-4878-4303-94ae-b3434d52612a-2.XSS婕忔礊娣卞害瑙ｆ瀽.png', 525008, '2025-04-03 20:38:08.664558', '/api/images/view/eb678908-4878-4303-94ae-b3434d52612a-2.XSS婕忔礊娣卞害瑙ｆ瀽.png'),
('image/png', '5780e906-42a1-4a88-ad06-d054bbf92735-3.鏂囦欢涓婁紶婕忔礊绐佺牬.png', '3.鏂囦欢涓婁紶婕忔礊绐佺牬.png', 'upload-dir/5780e906-42a1-4a88-ad06-d054bbf92735-3.鏂囦欢涓婁紶婕忔礊绐佺牬.png', 1350829, '2025-04-03 20:38:16.498729', '/api/images/view/5780e906-42a1-4a88-ad06-d054bbf92735-3.鏂囦欢涓婁紶婕忔礊绐佺牬.png');
