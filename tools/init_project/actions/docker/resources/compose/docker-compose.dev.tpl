services:
{{BACKEND_SERVICE}}
{{BOT_SERVICE}}
{{WORKER_SERVICE}}
{{REDIS_SERVICE}}
{{POSTGRES_SERVICE}}
{{NGINX_SERVICE}}

volumes:
{{VOLUMES}}

networks:
  {{PROJECT_NAME}}-network:
    driver: bridge
