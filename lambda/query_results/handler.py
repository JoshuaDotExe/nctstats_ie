"""
Lambda handler for querying NCT results from DynamoDB.

New compact format:
  Each item has  pk = "MODEL#<MAKE>#<MODEL>", sk = "TEST_YEAR#<year>"
  with a list attribute "d" containing base64-encoded percentage strings.

Endpoints:
  GET /results?make=FORD&model=FOCUS           → all test years for a model
  GET /results?make=FORD&model=FOCUS&year=2016  → specific test year for a model
"""

import json
import os
import boto3

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "eu-west-1"))
table = dynamodb.Table(os.environ.get("TABLE_NAME", "nct_results"))


def build_response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        },
        "body": json.dumps(body),
    }


def handler(event, context):
    params = event.get("queryStringParameters") or {}
    make = params.get("make", "").upper()
    model = params.get("model", "").upper()
    year = params.get("year")

    if not make or not model:
        return build_response(400, {"error": "make and model query parameters are required"})

    pk = f"MODEL#{make}#{model}"

    try:
        if year:
            # Query a specific test year (exact SK match)
            response = table.query(
                KeyConditionExpression="pk = :pk AND sk = :sk",
                ExpressionAttributeValues={
                    ":pk": pk,
                    ":sk": f"TEST_YEAR#{year}",
                },
            )
        else:
            # Query all test years for this model
            response = table.query(
                KeyConditionExpression="pk = :pk",
                ExpressionAttributeValues={":pk": pk},
            )

        return build_response(200, {
            "count": response["Count"],
            "items": response["Items"],
        })

    except Exception as e:
        return build_response(500, {"error": str(e)})
