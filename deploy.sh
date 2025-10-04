#!/bin/bash

# =============================================================================
# Video Animation Platform - Quick Deployment Script
# For Aliyun ECS with Docker
# =============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    log_error "Please run as root (use sudo)"
    exit 1
fi

log_info "Starting Video Animation Platform deployment..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    log_warn "Docker not found. Installing Docker..."
    curl -fsSL https://get.docker.com | bash
    systemctl start docker
    systemctl enable docker
    log_info "Docker installed successfully"
else
    log_info "Docker is already installed"
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    log_warn "Docker Compose not found. Installing..."
    curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    log_info "Docker Compose installed successfully"
else
    log_info "Docker Compose is already installed"
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    log_warn ".env file not found. Creating from template..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        log_warn "Please edit .env file with your configuration before proceeding"
        log_warn "Press Enter when ready..."
        read
    else
        log_error ".env.example not found"
        exit 1
    fi
else
    log_info ".env file found"
fi

# Create necessary directories
log_info "Creating necessary directories..."
mkdir -p logs logs/nginx ssl data uploads
chmod 755 logs logs/nginx

# Pull latest code (if git repo)
if [ -d ".git" ]; then
    log_info "Pulling latest code from git..."
    git pull || log_warn "Git pull failed or no remote configured"
fi

# Stop existing containers
if docker-compose -f docker-compose.prod.yml ps | grep -q "Up"; then
    log_info "Stopping existing containers..."
    docker-compose -f docker-compose.prod.yml down
fi

# Build and start services
log_info "Building and starting services..."
docker-compose -f docker-compose.prod.yml up -d --build

# Wait for services to be ready
log_info "Waiting for services to start..."
sleep 10

# Run database migrations
log_info "Running database migrations..."
docker-compose -f docker-compose.prod.yml exec -T app alembic upgrade head || log_warn "Migration failed or already up to date"

# Check service status
log_info "Checking service status..."
docker-compose -f docker-compose.prod.yml ps

# Test health endpoint
log_info "Testing health endpoint..."
sleep 5
if docker-compose -f docker-compose.prod.yml exec -T app curl -f http://localhost:8000/health > /dev/null 2>&1; then
    log_info "Health check passed!"
else
    log_warn "Health check failed. Check logs with: docker-compose -f docker-compose.prod.yml logs app"
fi

# Display access information
log_info "================================================"
log_info "Deployment completed successfully!"
log_info "================================================"
log_info ""
log_info "Services are running. Access them at:"
log_info "  - API Docs:    http://$(hostname -I | awk '{print $1}'):8000/docs"
log_info "  - Health:      http://$(hostname -I | awk '{print $1}'):8000/health"
log_info "  - Flower:      http://$(hostname -I | awk '{print $1}'):5555"
log_info "  - Prometheus:  http://$(hostname -I | awk '{print $1}'):9090"
log_info "  - Grafana:     http://$(hostname -I | awk '{print $1}'):3001"
log_info ""
log_info "Useful commands:"
log_info "  View logs:     docker-compose -f docker-compose.prod.yml logs -f app"
log_info "  Restart:       docker-compose -f docker-compose.prod.yml restart"
log_info "  Stop:          docker-compose -f docker-compose.prod.yml down"
log_info "  Status:        docker-compose -f docker-compose.prod.yml ps"
log_info ""
log_warn "Next steps:"
log_warn "  1. Configure SSL certificates (see DEPLOYMENT_DOCKER.md)"
log_warn "  2. Set up firewall rules"
log_warn "  3. Configure domain DNS"
log_warn "  4. Test all endpoints"
log_info "================================================"
