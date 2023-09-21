#!/bin/bash

path_to_staging = "" # update in  environment

# The  directory containing the code folders of the Branch --> to be changed in production 
iris_folder="$path_to_staging/STAGING_DIR/IRIS-NITK/IRIS"

log_path="$path_to_staging/STAGING_DIR/logs"

# Prefix comman to all the staging containers 

#prefix_string="staging_"
prefix_string="staging_iris-nitk_iris_" # for production


# get a list of  exited  docker container having  prefix=$prefix_string and the container should have been exited more than or equal to 24hrs ago
container_names=$(docker ps -a --filter 'status=exited' | grep  -E "days|weeks" | awk '{print $NF }'| grep "^$prefix_string"  )



for container_info in $container_names; do
    echo "Deleting old container : $container_info" >> $log_path
    docker rm "$container_info"
done


#Delete the corresponding code folders of  non existing containers 

# Get a list of code folders in the  directory . NOTE = session_store.rb is not a code folder
folder_names=$(ls "$iris_folder")

for folder_name in $folder_names; do
    container_name="${prefix_string}${folder_name}"

    # Check if the corresponding container exists
    if docker ps -a --format '{{.Names}}' | grep -q "$container_name"; then
        echo "Container exists for $folder_name" >> $log_path
    else
        folder_path="$iris_folder/$folder_name"
        rm -r "$folder_path"
        echo "Deleted folder: $folder_name"  >> $log_path
    fi
done

