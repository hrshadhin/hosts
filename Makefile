.PHONY: all

all: help

help: ## Display this help screen
	@grep -h -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'


########################
###  Build and TEST  ###
########################

build: ## Update hosts files
	@echo "updating hosts files..."
	@python update_hosts_file.py

build-min: ## Update hosts files and minimise output file
	@echo "updating minimise hosts file..."
	@python update_hosts_file.py -m

build-bb-list: ## Update block list for Blocky(DNS proxy)
	@echo "updating slim hosts file..."
	@python update_hosts_file.py -m -s -e -o bb_list.txt

build-for-hrs: ## Update files for HRS
	@echo "updating hosts files..."
	@python update_hosts_file.py
	@echo "*********** + ***********"
	@echo "updating slim hosts file..."
	@python update_hosts_file.py -n -nr -m -s -e -o bb_list.txt

test: ## Run unit tests
	@echo "running tests..."
	@python test_helpers.py

clean: ## Remove junk
	@rm -rf __pycache__ *.log


########################
###    GIT REMOTE    ###
########################

pull: ### Pull from git repository
	@echo "pulling changes from git remote"
	@git pull origin master

push: ### Push to git repository
	@echo "pushing changes to git remote"
	@git add .
	@git commit -m "update hosts"
	@git push -u origin master