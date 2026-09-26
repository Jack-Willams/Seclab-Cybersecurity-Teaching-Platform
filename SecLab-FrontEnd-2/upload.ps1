# First, build the project using yarn
yarn build

# Define variables for the server and file path
$server = "100.77.202.74"
$remotePath = "/var/www/"
$localPath = "./dist"

# Use SCP to transfer files
scp -r $localPath "work@${server}:${remotePath}"
