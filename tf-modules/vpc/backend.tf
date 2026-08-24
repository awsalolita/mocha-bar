terraform {
  backend "s3" {
    bucket       = "unicorn-star-tfstate"
    key          = "vpc/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }
}
