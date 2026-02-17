provider "aws" {
  region = "eu-west-1"
}

resource "aws_s3_bucket" "website_bucket" {
  bucket = "nctstats-ie-website-2026"
}

resource "aws_s3_bucket_website_configuration" "website_bucket" {
  bucket = aws_s3_bucket.website_bucket.id

  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "index.html"
  }
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
  }, split(".", each.value)[length(split(".", each.value)) - 1], "application/octet-stream")
}

resource "aws_s3_account_public_access_block" "website_bucket" {
  block_public_acls   = false
  block_public_policy = false
}

resource "aws_s3_bucket_public_access_block" "website_bucket" {
  bucket = aws_s3_bucket.website_bucket.id
  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
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
        Sid = "PublicReadGetObject"
        Effect = "Allow"
        Principal = "*"
        Action = [
          "s3:GetObject",
          "s3:ListBucket",
        ]
        Resource = [
          "${aws_s3_bucket.website_bucket.arn}",
          "${aws_s3_bucket.website_bucket.arn}/*"
        ]
      }
    ]
  })
}

output "website_endpoint" {
  value       = aws_s3_bucket_website_configuration.website_bucket.website_endpoint
  description = "The S3 website endpoint URL"
}

output "website_url" {
  value       = "http://${aws_s3_bucket_website_configuration.website_bucket.website_endpoint}"
  description = "The full website URL"
}