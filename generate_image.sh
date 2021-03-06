#!/bin/bash

if [ "$#" -ne 4 ]; then
    echo "The correct number of arguments is 3"
    exit 1
fi

#commands=("docker exec -it $1 mkdir /app" "docker exec -it $1 apk add --no-cache bash" "docker cp $2 $1:/app" "docker commit --change='ENTRYPOINT [\"/app/hello_world\"]' $1 $1/image:$3" "docker tag $1/image:$3 localhost:5000/$1/image:$3" "docker push localhost:5000/$1/image:$3")

#for command in "${commands[@]}"
#do
#    echo "Executing command \"$command\""
#    OUTPUT=$($command 2>&1)

#    if [ $? -ne 0 ]; then
#	printf "$OUTPUT\n"
#	exit 1
#    fi
#done

MKDIR="docker exec -it $1 mkdir /app"
BASH="docker exec -it $1 apk add --no-cache bash"
CP="docker cp $2 $1:/app"
COMMIT="docker commit --change='ENTRYPOINT [\"/app/$4\"]' $1 $1/image:$3"
SAVE="docker save $1/image:$3 -o /images/$1.tar.gz"
#TAG="docker tag $1/image:$3 localhost:5000/$1/image:$3"
#PUSH="docker push localhost:5000/$1/image:$3"

#echo $MKDIR
#echo $BASH
#echo $CP
#echo $COMMIT


echo $MKDIR
eval $MKDIR

echo $BASH
eval $BASH

echo $CP
eval $CP

echo $COMMIT
eval $COMMIT

echo $SAVE
eval $SAVE
#eval $TAG
#eval $PUSH
