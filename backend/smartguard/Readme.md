## Serverless deploy
First deploy:
```bash
AWS_PROFILE=edibusl serverless deploy --aws-s3-accelerate -v
```

## Serverless testing
Then invoke locally or in aws lambda using a mock file as an input
```bash
AWS_PROFILE=edibusl serverless invoke -f detectf --log -p mocks/detectf_s3_object_create_mock.json
AWS_PROFILE=edibusl serverless invoke local -f detectf --log -p mocks/detectf_s3_object_create_mock.json
```