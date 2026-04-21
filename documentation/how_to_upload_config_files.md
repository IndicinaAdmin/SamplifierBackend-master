# How to upload configuration files.

This document describes how to upload the configuration files for each measurement year. The configuration files contain the parameters for calculating the MRSS values.

**Very Important:** Do not delete the existing files for the 2020 measurement year. They were uploaded using AWS CDK, a tool to define infrastructure as code  that also manages the CI/CD pipeline. Deleting one of the files uploaded by CDK will cause the pipeline to crash on future executions, and it is not an easy fix.

![config_file_upload_video](./upload_image.gif)

When a configuration file is uploaded, its calculus parameters will be automatically extracted and stored in DynamoDB. This enables faster and cheaper future consulting of the calculus parameters.

**There are 4 types of configuration files:**

- reference_array
- measures_per_year
- measures_per_product
- single_rate_measures
- multi_rate_measures

## Where to upload
### The S3 Bucket name:
To find the S3 bucket first sign in to the AWS console and go to the [S3 console page](https://s3.console.aws.amazon.com/s3/home?region=us-east-1). The bucket that stores both the configuration and submission files is the one that starts with `samplifier-backend-api`.

### Path inside the bucket for the configuration files
To reduce the chances of errors, instead of using a specific pattern in the configuration files' names, we use specific folders for each configuration file type. The configuration files' path should follow the pattern below:  

```configs/<configuration_file_type>/<measurement_year>/<file_name>```  

The `configuration_file_type` should be one of the types listed previously, the `measurement_year` should be a four digit integer, and the `file_name` can be any name supported by S3 as long as it uses the correct file extension. Check the [accepted extensions](#accepted-file-types-and-extensions) bellow.

**Note:** Only when, and everytime, a file is correctly uploaded to a configuration folder, the calculus parameters will be automatically created/updated based on the uploaded file. Therefore:
1. If a new file is uploaded to a folder where another file already exists, the calculus parameters will be updated based on the new file.
2. Old files are not deleted when a new file is uploaded. However, S3 overwrites files with the same name on the same folder.
3. If a user uploads `File A` to a configuration folder, then uploads `File B`. The calculus parameters will first be based on `File A` and then updated based on `File B`. However, deleting `File B` will not cause the calculus parameters to revert to `File A`. The extraction of parameters is triggered only when a file is uploaded. To revert to `File A`, it is necessary to upload `File A` again.

#### Path examples
The files for the measurement year 2020 are already present in the S3 bucket, you can use their path as example. Just create new folders for each measurement year as necessary, and upload the files.

## File format
The configuration files should have specific extensions and the contents should be readable by the parameter extracting function.

### Accepted file types and extensions
All the files should be in the json format with the ".JSON" or ".json" extension. Except the reference_array files that can also be in the CSV format with the ".CSV" or ".csv" extension.

### Specific notes for CSV files
#### CSV separator
Values in each CSV row should be separated by one of the following characters:
- ','
- ';'
- '|'
- ' ' (single space)  
**Note:** The file has to use the same separator in all rows. You can not separate with commas on the first row and semicolons on the second row for example.

#### CSV headers
To ignore the CSV headers, the function that extracts the parameters from the configuration files, will skip any lines in the beginning of the file that:

- Contains the char sequence "inimum" or "mrss" or "MRSS"
- Is an empty line
- Is a line with just a single space

### File examples
The files for the measurement year 2020 are already in S3 and you can use them as examples. They are also in the [calc-config-files-2020](https://github.com/IndicinaMichael/SamplifierBackend/tree/master/calc-param-files-2020) folder of this GitHub repository.
