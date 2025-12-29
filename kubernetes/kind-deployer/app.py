###This application has been created to bootstrap a kind-cluster for kubernetes testing/development
###This is not intended to be used in a production environment and is used for development/research purposes only.


from flask import Flask, render_template, request, jsonify, Response
import subprocess
import threading
import json
import time
import webbrowser
import yaml
from datetime import datetime

app = Flask(__name__)

# Store deployment logs
deployment_logs = []
deployment_status = {"status": "idle", "progress": 0, "message": ""}

def log_message(message):
    """Add message to deployment logs"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    deployment_logs.append(log_entry)
    print(log_entry)

def run_command(cmd, description):
    """Run a shell command and log output"""
    log_message(f"Running: {description}")
    try:
        process = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = process.communicate()
        
        if process.returncode == 0:
            log_message(f"✓ {description} completed successfully")
            if stdout:
                for line in stdout.strip().split('\n'):
                    log_message(f"  {line}")
            return True, stdout
        else:
            log_message(f"✗ {description} failed")
            if stderr:
                for line in stderr.strip().split('\n'):
                    log_message(f"  ERROR: {line}")
            return False, stderr
    except Exception as e:
        log_message(f"✗ Exception during {description}: {str(e)}")
        return False, str(e)

def create_kind_config(config):
    """Generate Kind cluster configuration"""
    kind_config = {
        'kind': 'Cluster',
        'apiVersion': 'kind.x-k8s.io/v1alpha4',
        'name': config['cluster_name'],
        'nodes': []
    }
    
    # Add control plane nodes
    for i in range(config['control_plane_nodes']):
        node = {
            'role': 'control-plane',
        }
        if config['enable_ingress'] and i == 0:
            node['kubeadmConfigPatches'] = [
                'kind: InitConfiguration\nnodeRegistration:\n  kubeletExtraArgs:\n    node-labels: "ingress-ready=true"'
            ]
            node['extraPortMappings'] = [
                {'containerPort': 80, 'hostPort': 80, 'protocol': 'TCP'},
                {'containerPort': 443, 'hostPort': 443, 'protocol': 'TCP'}
            ]
        kind_config['nodes'].append(node)
    
    # Add worker nodes
    for i in range(config['worker_nodes']):
        kind_config['nodes'].append({'role': 'worker'})
    
    # Networking configuration
    if config.get('pod_subnet') or config.get('service_subnet'):
        kind_config['networking'] = {}
        if config.get('pod_subnet'):
            kind_config['networking']['podSubnet'] = config['pod_subnet']
        if config.get('service_subnet'):
            kind_config['networking']['serviceSubnet'] = config['service_subnet']
    
    return yaml.dump(kind_config)

def deploy_cluster(config):
    """Deploy Kind cluster with given configuration"""
    global deployment_status, deployment_logs
    
    deployment_logs = []
    deployment_status = {"status": "running", "progress": 0, "message": "Starting deployment..."}
    
    try:
        # Step 1: Check prerequisites
        deployment_status["progress"] = 10
        deployment_status["message"] = "Checking prerequisites..."
        log_message("=== Checking Prerequisites ===")
        
        success, _ = run_command("docker --version", "Checking Docker")
        if not success:
            deployment_status["status"] = "failed"
            deployment_status["message"] = "Docker is not installed or not running"
            return
        
        success, _ = run_command("kind --version", "Checking Kind")
        if not success:
            deployment_status["status"] = "failed"
            deployment_status["message"] = "Kind is not installed"
            return
        
        # Step 2: Delete existing cluster if requested
        if config.get('delete_existing', False):
            deployment_status["progress"] = 20
            deployment_status["message"] = "Deleting existing cluster..."
            log_message("=== Deleting Existing Cluster ===")
            run_command(f"kind delete cluster --name {config['cluster_name']}", 
                       f"Deleting cluster '{config['cluster_name']}'")
        
        # Step 3: Create Kind config file
        deployment_status["progress"] = 30
        deployment_status["message"] = "Generating cluster configuration..."
        log_message("=== Generating Kind Configuration ===")
        
        kind_config_yaml = create_kind_config(config)
        config_file = f"/tmp/kind-config-{config['cluster_name']}.yaml"
        
        with open(config_file, 'w') as f:
            f.write(kind_config_yaml)
        log_message(f"Config saved to {config_file}")
        log_message("Configuration:")
        for line in kind_config_yaml.split('\n'):
            log_message(f"  {line}")
        
        # Step 4: Create cluster
        deployment_status["progress"] = 40
        deployment_status["message"] = "Creating Kind cluster..."
        log_message("=== Creating Kind Cluster ===")
        
        create_cmd = f"kind create cluster --config {config_file}"
        if config.get('kubernetes_version'):
            create_cmd += f" --image kindest/node:{config['kubernetes_version']}"
        
        success, output = run_command(create_cmd, "Creating cluster")
        if not success:
            deployment_status["status"] = "failed"
            deployment_status["message"] = "Failed to create cluster"
            return
        
        # Step 5: Verify cluster
        deployment_status["progress"] = 70
        deployment_status["message"] = "Verifying cluster..."
        log_message("=== Verifying Cluster ===")
        
        run_command("kubectl cluster-info --context kind-" + config['cluster_name'], 
                   "Getting cluster info")
        run_command("kubectl get nodes", "Listing nodes")
        
        # Step 6: Install Ingress Controller if requested
        if config.get('enable_ingress', False):
            deployment_status["progress"] = 80
            deployment_status["message"] = "Installing NGINX Ingress Controller..."
            log_message("=== Installing NGINX Ingress Controller ===")
            
            run_command(
                "kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/kind/deploy.yaml",
                "Deploying NGINX Ingress Controller"
            )
            
            log_message("Waiting for ingress controller to be ready...")
            run_command(
                "kubectl wait --namespace ingress-nginx --for=condition=ready pod --selector=app.kubernetes.io/component=controller --timeout=90s",
                "Waiting for ingress controller"
            )
        
        # Step 7: Install MetalLB if requested
        if config.get('enable_metallb', False):
            deployment_status["progress"] = 90
            deployment_status["message"] = "Installing MetalLB..."
            log_message("=== Installing MetalLB ===")
            
            run_command(
                "kubectl apply -f https://raw.githubusercontent.com/metallb/metallb/v0.13.7/config/manifests/metallb-native.yaml",
                "Deploying MetalLB"
            )
            
            # Get Docker network subnet
            success, subnet = run_command(
                "docker network inspect -f '{{.IPAM.Config}}' kind | grep -oP '\\d+\\.\\d+\\.\\d+\\.\\d+/\\d+'",
                "Getting Docker network subnet"
            )
            
            if success and subnet:
                # Create IP address pool
                base_ip = '.'.join(subnet.strip().split('/')[0].split('.')[:-1])
                metallb_config = f"""
apiVersion: v1
kind: ConfigMap
metadata:
  namespace: metallb-system
  name: config
data:
  config: |
    address-pools:
    - name: default
      protocol: layer2
      addresses:
      - {base_ip}.200-{base_ip}.250
"""
                with open('/tmp/metallb-config.yaml', 'w') as f:
                    f.write(metallb_config)
                
                run_command("kubectl apply -f /tmp/metallb-config.yaml", "Configuring MetalLB")
        
        # Final status
        deployment_status["progress"] = 100
        deployment_status["status"] = "success"
        deployment_status["message"] = f"Cluster '{config['cluster_name']}' deployed successfully!"
        log_message("=== Deployment Complete ===")
        log_message(f"✓ Cluster '{config['cluster_name']}' is ready!")
        log_message(f"✓ Use: kubectl cluster-info --context kind-{config['cluster_name']}")
        
    except Exception as e:
        deployment_status["status"] = "failed"
        deployment_status["message"] = f"Deployment failed: {str(e)}"
        log_message(f"✗ Deployment failed with exception: {str(e)}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/deploy', methods=['POST'])
def deploy():
    """Start cluster deployment"""
    config = request.json
    
    # Start deployment in background thread
    thread = threading.Thread(target=deploy_cluster, args=(config,))
    thread.daemon = True
    thread.start()
    
    return jsonify({"status": "started"})

@app.route('/status')
def status():
    """Get deployment status"""
    return jsonify(deployment_status)

@app.route('/logs')
def logs():
    """Stream deployment logs"""
    def generate():
        last_index = 0
        while True:
            if len(deployment_logs) > last_index:
                for log in deployment_logs[last_index:]:
                    yield f"data: {json.dumps({'log': log})}\n\n"
                last_index = len(deployment_logs)
            time.sleep(0.5)
            
            if deployment_status["status"] in ["success", "failed"]:
                break
    
    return Response(generate(), mimetype='text/event-stream')

@app.route('/clusters')
def list_clusters():
    """List existing Kind clusters"""
    success, output = run_command("kind get clusters", "Listing clusters")
    if success:
        clusters = [c.strip() for c in output.strip().split('\n') if c.strip()]
        return jsonify({"clusters": clusters})
    return jsonify({"clusters": []})

if __name__ == '__main__':
    # Open browser automatically
    threading.Timer(1.5, lambda: webbrowser.open('http://localhost:5000')).start()
    
    print("=" * 60)
    print("Kind Cluster Deployer")
    print("=" * 60)
    print("Opening browser at http://localhost:5000")
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    
    app.run(debug=False, host='0.0.0.0', port=5000)
