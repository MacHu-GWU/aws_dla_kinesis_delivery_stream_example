.. _aws-kinesis-delivery-stream-examples:

AWS Kinesis Delivery Stream Examples
==============================================================================

.. contents::
    :class: this-will-duplicate-information-and-it-is-still-useful-here
    :depth: 1
    :local:


What is this Project
------------------------------------------------------------------------------
**这个 GitHub repo 的目的是能让开发者能快速实验 Kinesis Data Stream + Delivery Stream 的功能, 将其快速的部署到任何 AWS Account, 快速测试任何 Destination Integration.**

这个项目主要是提供了一套 CloudFormation Template, AWS Lambda for Transformation 的组合, 能一键生成所需资源, 并专注于实验系统功能.


How to Deploy this Example
------------------------------------------------------------------------------

**Prerequisites**:

1. Create an AWS Cloud 9 Dev Environment at https://console.aws.amazon.com/cloud9/home.

**Deploy Infrastructure**:

1. Create S3 bucket to store artifacts for CloudFormation / Lambda deployment: run `iac/s1_dependency.py <./iac/s1_dependency.py>`_
2. Create Infrastructure, Data S3 bucket, IAM Role for lambda and firehose, opensearch cluster, kinesis data stream: `iac/s2_app.py <./iac/s2_app.py>`_. make sure you COMMENT OUT ``stack.rg5`` and ``stack.rg6``.
3. Deploy AWS Lambda function, which is the dependency of firehose
    1. deploy lambda dependency layer: `bin/11-lbd-build-and-deploy-layer.sh <./bin/11-lbd-build-and-deploy-layer.sh>`_ (run this in Cloud 9)
    2. update AWS Charlice config: `lambda_app/update_charlice_config.py <./lambda_app/update_charlice_config.py>`_
    3. deploy lambda functions: `bin/12-lbd-deploy.sh <./12-lbd-deploy.sh>`_
4. Deploy kinesis delivery stream: `iac/s2_app.py <./iac/s2_app.py>`_. make sure you UNCOMMENT
``stack.rg5`` and ``stack.rg6``.


Destination
------------------------------------------------------------------------------

1. 数据到达 Data Stream
2. Delivery Stream 内部有个

S3 Destination
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



Benchmark
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Set up**

**Kinesis Stream**:

- Configuration: 10 shards
- Price:
    - Stream Shard: 10 * 24 * 30 * 0.015 = $108
    - Payload: 1 (per 100 records is 18KB) * 32 * 24 * 3600 * 30 / 1000000 * 0.014 = $1.16

**Lambda**:

- Configuration: 128MB, 2 sec per invoke
- Price:
    - n invoke per month: 24 * 60 * 30 * 10 = 432000
    - price: 432000 * 128 * 2 * 1000 * 0.0000000021 = $232

**OpenSearch Cluster**:

- Configuration: 3 + 3 (all r6g.large.search)
- Price: $771.15 / Month (https://calculator.aws/#/createCalculator/OpenSearchService)

**Total Monthly Price**:

- 108 + 232 + 771.15 = 1111.15

**Data**::

    {
        'id': 'bbec70d6-35eb-485f-9729-8465b9bda59f',
        'firstname': 'Jerry',
        'lastname': 'Snyder',
        'description': 'Mrs air in wife financial within live pull artist back.',
        'balance': 0
    }

**Data Characteristics**:

- 180KB per 1000 records in Kinesis IO
- 250KB per 1000 records in Opensearch Index (include index)
- 2500 TPS, 450 KB per seconds

**Experiment**

- Cloud9 m5.8xlarge, 32 vCPU, 128 GB memory, 10GB/s network
- 32 producer, send 100 records every 1 sec, for 10 minutes, total records = 32 * 100 * 10 * 60 = 1920000

**Data Producer Log**::

    this is producer: 12, has sent 59800 records. elapsed 742.896071 sec, all producer has sent 1919100 records. tps = 2583 records / sec
    this is producer: 4, has sent 59800 records. elapsed 742.897286 sec, all producer has sent 1919200 records. tps = 2583 records / sec
    this is producer: 17, has sent 59700 records. elapsed 742.897903 sec, all producer has sent 1919300 records. tps = 2583 records / sec
    this is producer: 12, has sent 59900 records. elapsed 743.672583 sec, all producer has sent 1919400 records. tps = 2580 records / sec
    this is producer: 4, has sent 59900 records. elapsed 743.673648 sec, all producer has sent 1919500 records. tps = 2581 records / sec
    this is producer: 17, has sent 59800 records. elapsed 743.67454 sec, all producer has sent 1919600 records. tps = 2581 records / sec
    this is producer: 17, has sent 59900 records. elapsed 744.442808 sec, all producer has sent 1919700 records. tps = 2578 records / sec
    this is producer: 12, has sent 60000 records. elapsed 744.450747 sec, all producer has sent 1919800 records. tps = 2578 records / sec
    this is producer: 4, has sent 60000 records. elapsed 744.452125 sec, all producer has sent 1919900 records. tps = 2578 records / sec
    this is producer: 17, has sent 60000 records. elapsed 745.182325 sec, all producer has sent 1920000 records. tps = 2576 records / sec
    elapse 745.19 sec
    has sent 1920000

**Results**

**S3 Status**::

    to-s3/03-success/ has 1920000 records

**OpenSearch Status**::

    {
        'count': 1920000,
        '_shards': {'total': 24, 'successful': 24, 'skipped': 0, 'failed': 0}
    }
