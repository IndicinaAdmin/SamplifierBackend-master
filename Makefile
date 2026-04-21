# CDK targets
cdk-install:
	npm install

cdk-build: #cdk-install
	npm run build

cdk-watch:
	npm run watch

cdk-test: cdk-build
	npm run test

cdk-pr: cdk-build
	npx cdk synth


cdk-e2e: cdk-build #to execute this cmd, this app must be exists in aws
	npm run e2e -- --funcName=$(funcName) --accessKey=$(accessKey) --seckey=$(seckey)
	
cdk-bootstrap:
	npx cdk bootstrap \
	--cloudformation-execution-policies \
	arn:aws:iam::aws:policy/AdministratorAccess

cdk-synth:
	cdk synth

cdk-deploy: cdk-bootstrap
	npx cdk deploy

# Runtime

runtime-pr:
	cd runtime && $(MAKE) pr

runtime-int-test:
	cd runtime && $(MAKE) integ-test