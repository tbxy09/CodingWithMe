#!/bin/bash

# Initialize the project as a Git repository
git init

# Add all files to the repository
git add .

# Commit the changes
git commit -m "Initial commit"

# Set the remote to http://150.109.60.238:3000/tbxy09/MetaAgent.git with name and password
git config --local user.name "$USER_NAME"
git config --local user.email "test@test.com"
# git config --local user.password $PASSWORD
git remote add origin $GOGS/$USER_NAME/MetaAgent.git

# Push the changes to the remote repository
git push --set-upstream origin master
git push -u origin --use-token $GITHUB_API_TOKEN master