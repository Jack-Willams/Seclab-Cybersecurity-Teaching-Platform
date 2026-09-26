-- Clear the old shared default avatar so users without uploaded avatars remain blank.
UPDATE `user`
SET `user_image` = NULL
WHERE `user_image` = '/example.png';
