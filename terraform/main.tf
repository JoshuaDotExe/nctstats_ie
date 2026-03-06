provider "aws" {
  region = "eu-west-1"
}

provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
}

resource "aws_acm_certificate" "site" {
  provider          = aws.us_east_1
  domain_name       = "nctstats.ie"
  subject_alternative_names = ["www.nctstats.ie"]
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

output "acm_validation_records" {
  value       = aws_acm_certificate.site.domain_validation_options
  description = "Add these CNAME records to your DNS provider to validate the ACM certificate"
}

resource "aws_s3_bucket" "website_bucket" {
  bucket = "nctstats-ie-website-2026"
}

resource "aws_s3_object" "website_files" {
  for_each = fileset("${path.module}/../app/dist", "**/*")
  
  bucket       = aws_s3_bucket.website_bucket.id
  key          = each.value
  source       = "${path.module}/../app/dist/${each.value}"
  etag         = filemd5("${path.module}/../app/dist/${each.value}")
  content_type = lookup({
    "html" = "text/html"
    "css"  = "text/css"
    "js"   = "application/javascript"
    "json" = "application/json"
    "png"  = "image/png"
    "jpg"  = "image/jpeg"
    "jpeg" = "image/jpeg"
    "gif"  = "image/gif"
    "svg"  = "image/svg+xml"
    "ico"  = "image/x-icon"
    "woff" = "font/woff"
    "woff2" = "font/woff2"
    "ttf"  = "font/ttf"
    "eot"  = "application/vnd.ms-fontobject"
    "pdf"  = "application/pdf"
    "docx" = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
  }, split(".", each.value)[length(split(".", each.value)) - 1], "application/octet-stream")
}

resource "aws_s3_account_public_access_block" "website_bucket" {
  block_public_acls   = true
  block_public_policy = true
}

resource "aws_s3_bucket_public_access_block" "website_bucket" {
  bucket = aws_s3_bucket.website_bucket.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_cloudfront_origin_access_control" "site" {
  name                              = "nctstats-s3-oac"
  description                       = "OAC for NCT Stats S3 bucket"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_s3_bucket_policy" "website_bucket" {
  bucket = aws_s3_bucket.website_bucket.id

  depends_on = [
    aws_s3_account_public_access_block.website_bucket,
    aws_s3_bucket_public_access_block.website_bucket
  ]

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowCloudFrontOAC"
        Effect = "Allow"
        Principal = {
          Service = "cloudfront.amazonaws.com"
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.website_bucket.arn}/*"
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.site.arn
          }
        }
      }
    ]
  })
}

resource "aws_cloudfront_distribution" "site" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "NCT Stats website"
  default_root_object = "index.html"
  aliases             = ["nctstats.ie", "www.nctstats.ie"]

  origin {
    domain_name              = aws_s3_bucket.website_bucket.bucket_regional_domain_name
    origin_id                = "nctstats-s3-website"
    origin_access_control_id = aws_cloudfront_origin_access_control.site.id
  }

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD", "OPTIONS"]
    target_origin_id = "nctstats-s3-website"

    viewer_protocol_policy = "redirect-to-https"
    compress               = true

    forwarded_values {
      query_string = false

      cookies {
        forward = "none"
      }
    }
  }

  custom_error_response {
    error_code         = 403
    response_code      = 200
    response_page_path = "/index.html"
  }

  custom_error_response {
    error_code         = 404
    response_code      = 200
    response_page_path = "/index.html"
  }

  price_class = "PriceClass_100"

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    acm_certificate_arn      = aws_acm_certificate.site.arn
    ssl_support_method       = "sni-only"
    minimum_protocol_version = "TLSv1.2_2021"
  }
}

output "cloudfront_domain" {
  value       = aws_cloudfront_distribution.site.domain_name
  description = "CloudFront distribution domain — create a CNAME record pointing your domain to this value"
}

output "cloudfront_distribution_id" {
  value       = aws_cloudfront_distribution.site.id
  description = "CloudFront distribution ID (useful for cache invalidation)"
}

resource "aws_dynamodb_table" "nct_results" {
  name         = "nct_results"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"
  range_key    = "sk"

  attribute {
    name = "pk"
    type = "S"
  }

  attribute {
    name = "sk"
    type = "S"
  }

  attribute {
    name = "test_year"
    type = "N"
  }

  global_secondary_index {
    name            = "by_test_year"
    hash_key        = "test_year"
    range_key       = "pk"
    projection_type = "ALL"
  }

  tags = {
    Project = "nctstats"
  }
}

output "dynamodb_table_name" {
  value       = aws_dynamodb_table.nct_results.name
  description = "DynamoDB table name for NCT results"
}

output "dynamodb_table_arn" {
  value       = aws_dynamodb_table.nct_results.arn
  description = "DynamoDB table ARN"
}

# --- Lambda ---

data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../lambda/query_results"
  output_path = "${path.module}/../lambda/query_results.zip"
}

resource "aws_iam_role" "lambda_exec" {
  name = "nctstats-lambda-exec"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda_dynamo" {
  name = "nctstats-lambda-dynamo"
  role = aws_iam_role.lambda_exec.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:Query",
          "dynamodb:GetItem",
        ]
        Resource = [
          aws_dynamodb_table.nct_results.arn,
          "${aws_dynamodb_table.nct_results.arn}/index/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
        ]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

resource "aws_lambda_function" "query_results" {
  function_name    = "nctstats-query-results"
  handler          = "handler.handler"
  runtime          = "python3.12"
  role             = aws_iam_role.lambda_exec.arn
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  timeout          = 10
  memory_size      = 128

  environment {
    variables = {
      TABLE_NAME = aws_dynamodb_table.nct_results.name
    }
  }

  tags = {
    Project = "nctstats"
  }
}

# --- API Gateway ---

resource "aws_apigatewayv2_api" "api" {
  name          = "nctstats-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["https://nctstats.ie", "https://www.nctstats.ie", "http://localhost:5173"]
    allow_methods = ["GET", "OPTIONS"]
    allow_headers = ["Content-Type"]
    max_age       = 3600
  }
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.api.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.query_results.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "get_results" {
  api_id    = aws_apigatewayv2_api.api.id
  route_key = "GET /results"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.query_results.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.api.execution_arn}/*/*"
}

output "api_endpoint" {
  value       = aws_apigatewayv2_api.api.api_endpoint
  description = "API Gateway endpoint URL"
}