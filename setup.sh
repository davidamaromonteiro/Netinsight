#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════
# NetInsight — Script de déploiement automatique
# Usage : chmod +x setup.sh && ./setup.sh
# ═══════════════════════════════════════════════════════════════════════
set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; CYAN='\033[0;36m'; NC='\033[0m'
echo -e "${CYAN}╔════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   NetInsight — Déploiement automatique    ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════╝${NC}"
echo ""

# 1. Vérification Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker n'est pas installé.${NC}"
    echo "   Installez Docker : https://docs.docker.com/engine/install/"
    exit 1
fi
echo -e "${GREEN}✅ Docker détecté${NC}"

if ! docker compose version &> /dev/null; then
    echo -e "${RED}❌ Docker Compose n'est pas disponible.${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Docker Compose détecté${NC}"

# 2. Configuration .env
if [ ! -f backend/.env ]; then
    echo -e "${CYAN}📝 Création du fichier backend/.env...${NC}"
    cp backend/.env.example backend/.env
    
    # Générer une SECRET_KEY aléatoire
    SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || openssl rand -base64 32)
    sed -i "s/change-me-to-a-long-random-string/$SECRET/" backend/.env
    echo -e "${GREEN}✅ .env créé avec une clé secrète aléatoire${NC}"
else
    echo -e "${GREEN}✅ backend/.env existe déjà${NC}"
fi

# 3. Build & Lancement
echo ""
echo -e "${CYAN}🔨 Construction des images Docker...${NC}"
docker compose build --quiet

echo ""
echo -e "${CYAN}🚀 Démarrage des services...${NC}"
docker compose up -d

# 4. Attente santé
echo ""
echo -e "${CYAN}⏳ Attente de la santé des services...${NC}"
MAX_WAIT=120
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Backend healthy${NC}"
        break
    fi
    sleep 2
    WAITED=$((WAITED + 2))
    echo -n "."
done
echo ""

# 5. Seed données de test
echo ""
echo -e "${CYAN}🗄️  Chargement des données de test...${NC}"
docker exec netinsight-backend python /app/seed_test_data.py 2>/dev/null && \
    echo -e "${GREEN}✅ Données de test chargées${NC}" || \
    echo -e "${CYAN}   (seed déjà exécuté ou base non vide)${NC}"

# 6. Résumé
echo ""
echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   🎉 NetInsight est opérationnel !         ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
echo ""
echo -e "  Frontend   : ${CYAN}http://localhost${NC}"
echo -e "  API/Swagger: ${CYAN}http://localhost:8000/docs${NC}"
echo -e "  ACME Store : ${CYAN}http://localhost:8080${NC}    (cible SQLmap)"
echo ""
echo -e "  Login      : ${CYAN}admin@netinsight.io${NC} / ${CYAN}Admin123!${NC}"
echo ""
echo -e "  Outils intégrés : Nmap • Banner Grabbing • SQLmap • Nikto"
echo -e "  Rapports        : MITRE ATT&CK • Cyber Kill Chain • CVE/NVD"
echo ""
