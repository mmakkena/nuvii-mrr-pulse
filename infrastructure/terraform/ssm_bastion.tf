# MRRPulse Infrastructure - SSM Bastion
# Provides secure DB access from laptop via SSM port forwarding
# No key pair, no open SSH port - SSM agent handles the tunnel over HTTPS

data "aws_ami" "amazon_linux_2" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }
}

resource "aws_iam_role" "ssm_bastion" {
  name = "${local.name_prefix}-ssm-bastion-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ssm_bastion" {
  role       = aws_iam_role.ssm_bastion.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "ssm_bastion" {
  name = "${local.name_prefix}-ssm-bastion-profile"
  role = aws_iam_role.ssm_bastion.name
}

resource "aws_security_group" "ssm_bastion" {
  name        = "${local.name_prefix}-ssm-bastion-sg"
  description = "SSM bastion - no inbound, outbound to RDS and SSM endpoints"
  vpc_id      = aws_vpc.main.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${local.name_prefix}-ssm-bastion-sg"
  }
}

resource "aws_instance" "ssm_bastion" {
  ami                         = data.aws_ami.amazon_linux_2.id
  instance_type               = "t3.micro"
  subnet_id                   = aws_subnet.public[0].id
  iam_instance_profile        = aws_iam_instance_profile.ssm_bastion.name
  vpc_security_group_ids      = [aws_security_group.ssm_bastion.id]
  associate_public_ip_address = true

  # SSM agent is pre-installed on Amazon Linux 2
  # No key_name — access only via SSM Session Manager

  tags = {
    Name = "${local.name_prefix}-ssm-bastion"
  }
}
