# Infraestructura GCP mínima para el pipeline de e-commerce

Este repositorio crea exclusivamente la primera etapa en GCP:

```text
VPC personalizada → subred → Compute Engine (preparada para PostgreSQL)
Simulador de eventos → Pub/Sub topic → suscripción batch + suscripción streaming
```

No crea AWS, Azure, Cloud Run, Cloud Storage, BigQuery, Cloud SQL, GKE ni servicios de procesamiento. PostgreSQL se instalará más adelante dentro de la VM; Terraform solo deja lista su infraestructura.

## Recursos

- Una VPC en modo personalizado y una subred regional.
- Una VM Debian 12 `e2-small` con disco `pd-balanced` de 30 GB, una configuración razonable y de bajo costo para el entorno académico.
- Cloud Router y Cloud NAT para salida de actualizaciones sin asignar una IP pública a la VM.
- Una cuenta de servicio dedicada para la VM, con solo escritura de logs y métricas.
- Un tópico de Pub/Sub con dos suscripciones *pull* independientes —batch y streaming—, ambas con retención de siete días. Las suscripciones filtran los atributos `batch` y `streaming`: un evento se entrega a cada suscripción cuyo atributo sea `"true"`. Pub/Sub es administrado, por lo que no pertenece a la VPC ni recibe una subred.
- APIs de Compute Engine, Pub/Sub e IAM necesarias para estos recursos.

## Seguridad y acceso administrativo

La VM no tiene IP pública: solo recibe una IP privada en la subred. El acceso administrativo usa el túnel TCP de IAP y OS Login. Autoriza a cada administrador tanto en `iap_tunnel_members` como en `admin_os_login_members`; por ejemplo `user:tu-correo@universidad.edu`.

La única regla SSH permite TCP/22 desde `35.235.240.0/20`, el rango de IAP, y se aplica solo al tag `allow-iap-ssh` de esta VM. No se abre TCP/5432: PostgreSQL deberá consumirse por IP privada mediante redes autorizadas, o mediante un túnel SSH/IAP cuando se instale.

La service account de la VM PostgreSQL recibe automáticamente `roles/pubsub.publisher` únicamente sobre el tópico de eventos. Los permisos Pub/Sub adicionales se asignan mediante `pubsub_publisher_members`, `pubsub_batch_subscriber_members` y `pubsub_stream_subscriber_members`; no se otorgan roles amplios a nivel de proyecto. Añade las identidades del simulador y de cada consumidor cuando existan.

## Configuración

1. Autentícate con ADC:

   ```bash
   gcloud auth application-default login
   ```

2. Crea un archivo local `terraform.tfvars` (no lo subas si contiene datos sensibles):

   ```hcl
   project_id = "mi-proyecto-gcp"
   region     = "us-central1"
   zone       = "us-central1-a"

   admin_os_login_members = [
     "user:tu-correo@universidad.edu",
   ]
   iap_tunnel_members = [
     "user:tu-correo@universidad.edu",
   ]

   # Rellénalos cuando el simulador y el proceso consumidor tengan identidad.
   pubsub_publisher_members         = []
   pubsub_batch_subscriber_members  = []
   pubsub_stream_subscriber_members = []
   ```

3. Ejecuta:

   ```bash
   terraform init
   terraform fmt -recursive
   terraform validate
   terraform plan
   ```

No ejecutes `terraform apply` sin revisar el plan y contar con autorización.

Para conectarte después del despliegue:

```bash
gcloud compute ssh demo-dev-postgresql \
  --zone=us-central1-a \
  --tunnel-through-iap
```

Sustituye el nombre y la zona por los outputs `instance_name` e `instance_zone`.

## Variables principales

`region`, `zone`, `vpc_name`, `subnet_name`, `subnet_cidr`, `instance_name`, `machine_type`, `boot_disk_size_gb`, `pubsub_topic_name`, `pubsub_batch_subscription_name` y `pubsub_stream_subscription_name` tienen valores por defecto y se pueden sobrescribir desde `terraform.tfvars`. Los recursos se prefijan con `name_prefix` y `environment`.

Los outputs informan la VPC, subred, nombre/IP/zona de la VM y los IDs del tópico y de las suscripciones batch y streaming de Pub/Sub.

## Filtrado de eventos Pub/Sub

El simulador publica cada evento una sola vez en `demo-dev-user-events`. El Pub/Sub filtra cada evento con 