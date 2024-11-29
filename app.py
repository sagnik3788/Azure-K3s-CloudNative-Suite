from fastapi import FastAPI, HTTPException
import subprocess
import os

app = FastAPI()

# Path to your Terraform configuration
TERRAFORM_DIR = "./"

@app.post("/create-cluster")
async def create_cluster():
    """Creates a K3s cluster using Terraform."""
    try:
        # Navigate to the Terraform directory
        os.chdir(TERRAFORM_DIR)

        # Run Terraform commands to initialize and apply configuration
        subprocess.run(["terraform", "init"], check=True)
        subprocess.run(["terraform", "apply", "-auto-approve"], check=True)

        return {"message": "K3s cluster created successfully"}
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Error creating cluster: {e.stderr}")
