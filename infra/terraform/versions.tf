terraform {
  # 1.16 y no 1.9: el estado de production lo escribio un 1.16.1, y Terraform
  # se niega a operar un estado que escribio una version mas nueva. Con el
  # limite bajo, un binario viejo pasaba esta comprobacion y fallaba despues
  # con un error sobre el estado, que no dice que hay que actualizar.
  required_version = ">= 1.16"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # El estado guarda la contrasena de la base en claro. En local eso es un
  # archivo sin cifrar en el disco de quien aplique; compartido entre dos
  # personas, dos estados que se pisan.
  #
  # Crear el bucket una vez, a mano, y descomentar:
  #
  #   gsutil mb -l northamerica-south1 gs://fierro-tfstate
  #   gsutil versioning set on gs://fierro-tfstate
  #
  # backend "gcs" {
  #   bucket = "fierro-tfstate"
  #   prefix = "fierro"
  # }
}

provider "google" {
  project = var.project_id
  region  = var.region
}
