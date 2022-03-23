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
1. `Run iac/s1_dependency.py <./iac/s1_dependency.py>`_


Destination
------------------------------------------------------------------------------

1. 数据到达 Data Stream
2. Delivery Stream 内部有个

S3 Destination
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~



OpenSearch Destination
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
