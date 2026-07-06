# EvoTime

EvoTime is a modern Django-based e-commerce platform featuring dynamic user experiences, an integrated shopping cart, product management, wishlist functionality, and a secure checkout process. It utilizes Tailwind CSS for a sleek and responsive UI and integrates with various third-party services like Razorpay for payments, Cloudinary for media storage, and Google for social authentication.

## Features

- **User Authentication**: Secure signup and login process with options for Email verification and Google OAuth integration using `django-allauth`.
- **Product Management**: A robust catalog supporting varied products.
- **Cart & Wishlist**: Seamless shopping cart and wishlist management.
- **Payment Gateway**: Integrated with Razorpay for secure online payments.
- **Media Storage**: Cloudinary integration for scalable and fast image/media delivery.
- **Modern UI**: Styled with Tailwind CSS directly via CDN.

## Tech Stack

- **Backend**: Django (Python 3)
- **Database**: PostgreSQL
- **Frontend**: HTML5, Vanilla JavaScript, Tailwind CSS (CDN)
- **Services**: Razorpay, Cloudinary, Google OAuth

## Prerequisites

Ensure you have the following installed on your system:
- [Python 3.8+](https://www.python.org/downloads/)
- [PostgreSQL](https://www.postgresql.org/download/)
- [Git](https://git-scm.com/downloads)

## Local Development Setup

Follow these steps to get your development environment running:

### 1. Clone the repository

```bash
git clone <your-repository-url>
cd EvoTime
```

### 2. Create and activate a Virtual Environment

It is recommended to isolate your project dependencies using a virtual environment.

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

Navigate to the source directory and install the required Python packages:

```bash
cd EvoTime
pip install -r requirements.txt
```

### 4. Configure Environment Variables

The project uses `python-decouple` to manage environment variables. You will need to create a `.env` file inside the inner `EvoTime` folder (the same directory as `settings.py` and `manage.py`) with the following necessary keys:

```ini
# Django Settings
SECRET_KEY=your_django_secret_key
DEBUG=True

# Database Configuration
DATABASE_NAME=your_db_name
DATABASE_USER=your_db_user
DATABASE_PASSWORD=your_db_password
DATABASE_HOST=localhost
DATABASE_PORT=5432

# Cloudinary Storage Settings
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret

# Razorpay Settings
RAZORPAY_KEY_ID=your_razorpay_key_id
RAZORPAY_KEY_SECRET=your_razorpay_key_secret

# Google OAuth (For Social Login)
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# Email Configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password
```

### 5. Setup the Database

Create your PostgreSQL database matching the credentials you supplied in your `.env` file, and then run the Django migrations:

```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Create a Superuser

To access the Django Admin panel, create a superuser account:

```bash
python manage.py createsuperuser
```

### 7. Run the Development Server

Start the local Django server:

```bash
python manage.py runserver
```

You can now view the application at `http://127.0.0.1:8000/`.

## Application Structure

- `admin_home/` - Handles the admin dashboard and metrics.
- `user_home/` - Manages user profiles, authentication (login, signup, OTP), and home page.
- `Products/` - App dedicated to the product catalog.
- `Cart/` - Handles cart operations.
- `Wishlist/` - Manages user favorite items.
- `templates/` - Contains all HTML files formatted with Tailwind CSS classes.
- `static/` - Stores raw static files like custom CSS, images, or JS logic.
