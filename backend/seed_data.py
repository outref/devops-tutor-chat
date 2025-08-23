import asyncio
import os
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from app.services.rag_service import RAGService
from app.services.database import engine, Base

load_dotenv()

# DevOps content for seeding
DEVOPS_CONTENT = [
    {
        "title": "Kubernetes Fundamentals",
        "topic": "kubernetes",
        "content": """Kubernetes (K8s) is an open-source container orchestration platform that automates the deployment, scaling, and management of containerized applications. Key concepts include:

        - Pods: The smallest deployable unit, containing one or more containers
        - Services: Provide stable networking and load balancing
        - Deployments: Manage the desired state of your application
        - ConfigMaps and Secrets: Store configuration data and sensitive information
        - Namespaces: Provide resource isolation and organization
        
        Common kubectl commands:
        - kubectl get pods: List all pods
        - kubectl describe pod <name>: Get detailed pod information
        - kubectl apply -f <file>: Apply configuration from YAML file
        - kubectl logs <pod>: View pod logs
        - kubectl exec -it <pod> -- /bin/bash: Access pod shell"""
    },
    {
        "title": "Docker Containerization",
        "topic": "docker",
        "content": """Docker is a platform for developing, shipping, and running applications in containers. Containers package an application with all its dependencies, ensuring consistency across environments.

        Key Docker concepts:
        - Images: Read-only templates containing application code and dependencies
        - Containers: Running instances of images
        - Dockerfile: Text file with instructions to build images
        - Docker Registry: Repository for storing and sharing images
        - Volumes: Persistent data storage for containers
        
        Essential Docker commands:
        - docker build -t <name> .: Build image from Dockerfile
        - docker run -d -p 8080:80 <image>: Run container in detached mode
        - docker ps: List running containers
        - docker logs <container>: View container logs
        - docker-compose up: Start multi-container applications"""
    },
    {
        "title": "CI/CD Pipeline Best Practices",
        "topic": "cicd",
        "content": """Continuous Integration and Continuous Deployment (CI/CD) automates the software delivery process. A typical pipeline includes:

        1. Source Control: Git-based version control
        2. Build Stage: Compile code and run unit tests
        3. Test Stage: Execute integration and acceptance tests
        4. Security Scanning: Check for vulnerabilities
        5. Artifact Creation: Package application for deployment
        6. Deployment: Release to staging/production environments
        
        Popular CI/CD tools:
        - Jenkins: Open-source automation server
        - GitLab CI/CD: Integrated with GitLab
        - GitHub Actions: Native GitHub automation
        - CircleCI: Cloud-based CI/CD platform
        - ArgoCD: GitOps continuous delivery for Kubernetes"""
    },
    {
        "title": "AWS CLI Essential Commands",
        "topic": "aws",
        "content": """The AWS Command Line Interface (CLI) enables programmatic access to AWS services. Common commands include:

        EC2 Management:
        - aws ec2 describe-instances: List EC2 instances
        - aws ec2 start-instances --instance-ids <id>: Start instances
        - aws ec2 create-snapshot --volume-id <id>: Create EBS snapshot
        
        S3 Operations:
        - aws s3 ls: List S3 buckets
        - aws s3 cp file.txt s3://bucket/: Upload file
        - aws s3 sync ./local s3://bucket/: Sync directory
        
        IAM Management:
        - aws iam list-users: List IAM users
        - aws iam create-role --role-name <name>: Create IAM role
        
        CloudFormation:
        - aws cloudformation create-stack: Deploy infrastructure
        - aws cloudformation describe-stacks: View stack details"""
    },
    {
        "title": "Google Cloud CLI (gcloud) Essentials",
        "topic": "gcloud",
        "content": """The gcloud CLI is the primary command-line tool for Google Cloud Platform. Key commands:

        Project Management:
        - gcloud config set project <project-id>: Set active project
        - gcloud projects list: List all projects
        
        Compute Engine:
        - gcloud compute instances list: List VM instances
        - gcloud compute instances create <name>: Create new instance
        - gcloud compute ssh <instance>: SSH into instance
        
        Kubernetes Engine (GKE):
        - gcloud container clusters create <name>: Create GKE cluster
        - gcloud container clusters get-credentials <name>: Configure kubectl
        
        Storage:
        - gcloud storage buckets list: List Cloud Storage buckets
        - gcloud storage cp file.txt gs://bucket/: Upload file
        
        IAM:
        - gcloud iam service-accounts create <name>: Create service account
        - gcloud projects add-iam-policy-binding: Grant permissions"""
    },
    {
        "title": "Terraform Infrastructure as Code",
        "topic": "terraform",
        "content": """Terraform enables infrastructure provisioning through declarative configuration files. Core concepts:

        - Providers: Plugins for interacting with cloud providers
        - Resources: Infrastructure components to create
        - Variables: Parameterize configurations
        - Outputs: Export values from configurations
        - State: Track infrastructure changes
        
        Basic Terraform workflow:
        1. terraform init: Initialize working directory
        2. terraform plan: Preview infrastructure changes
        3. terraform apply: Create/update infrastructure
        4. terraform destroy: Remove infrastructure
        
        Example configuration:
        ```hcl
        provider "aws" {
          region = "us-west-2"
        }
        
        resource "aws_instance" "web" {
          ami           = "ami-0c55b159cbfafe1f0"
          instance_type = "t2.micro"
          
          tags = {
            Name = "WebServer"
          }
        }
        ```"""
    },
    {
        "title": "Ansible Automation",
        "topic": "ansible",
        "content": """Ansible is an agentless automation tool for configuration management, application deployment, and orchestration. Key concepts:

        - Inventory: List of managed hosts
        - Playbooks: YAML files defining automation tasks
        - Modules: Units of work (e.g., copy files, install packages)
        - Roles: Reusable collections of tasks
        - Variables: Dynamic values in playbooks
        
        Common Ansible commands:
        - ansible-playbook site.yml: Run playbook
        - ansible all -m ping: Test connectivity
        - ansible-inventory --list: View inventory
        - ansible-vault encrypt secrets.yml: Encrypt sensitive data
        
        Example playbook:
        ```yaml
        ---
        - hosts: webservers
          tasks:
            - name: Install nginx
              apt:
                name: nginx
                state: present
            - name: Start nginx service
              service:
                name: nginx
                state: started
        ```"""
    },
    {
        "title": "Monitoring with Prometheus and Grafana",
        "topic": "monitoring",
        "content": """Prometheus is an open-source monitoring system with a time-series database, while Grafana provides visualization dashboards.

        Prometheus concepts:
        - Metrics: Time-series data (counters, gauges, histograms)
        - Exporters: Expose metrics from applications
        - PromQL: Query language for metrics
        - Alerting: Define alert rules and notifications
        - Service Discovery: Automatically find monitoring targets
        
        Grafana features:
        - Dashboards: Customizable visualization panels
        - Data Sources: Connect to Prometheus, InfluxDB, etc.
        - Alerts: Visual alert configuration
        - Variables: Dynamic dashboard parameters
        
        Common PromQL queries:
        - rate(http_requests_total[5m]): Request rate over 5 minutes
        - avg(cpu_usage_percent) by (instance): Average CPU by instance
        - histogram_quantile(0.95, ...): 95th percentile latency"""
    }
]

async def seed_database():
    """Seed the database with DevOps content"""
    # Initialize services
    embeddings = OpenAIEmbeddings(api_key=os.getenv("OPENAI_API_KEY"))
    rag_service = RAGService(embeddings)
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print("Seeding database with DevOps content...")
    
    # Add documents
    try:
        ids = await rag_service.add_documents_batch(DEVOPS_CONTENT)
        print(f"Successfully added {len(ids)} document chunks to the database")
    except Exception as e:
        print(f"Error seeding database: {e}")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed_database())
