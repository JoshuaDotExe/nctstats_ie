"""
Lambda handler for querying NCT results from DynamoDB.

Endpoints:
  GET /results?make=FORD&model=FOCUS           → all test years for a model
  GET /results?make=FORD&model=FOCUS&year=2016  → specific test year for a model
"""

import json
import os
import boto3
from decimal import Decimal

dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "eu-west-1"))
table = dynamodb.Table(os.environ.get("TABLE_NAME", "nct_results"))


class DecimalEncoder(json.JSONEncoder):
    """Handle Decimal types returned by DynamoDB."""
    def default(self, o):
        if isinstance(o, Decimal):
            return int(o) if o % 1 == 0 else float(o)
        return super().default(o)


def build_response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        },
        "body": json.dumps(body, cls=DecimalEncoder),
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
            # Query a specific test year
            response = table.query(
                KeyConditionExpression="pk = :pk AND begins_with(sk, :skprefix)",
                ExpressionAttributeValues={
                    ":pk": pk,
                    ":skprefix": f"TEST_YEAR#{year}#",
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
