# Flask API

A simple Flask REST API with CRUD operations for managing items.

## Installation

1. Clone the repository:
```bash
git clone https://github.com/cksit012010/myRepository.git
cd myRepository
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the API

Start the Flask development server:
```bash
python app.py
```

The API will be available at `http://localhost:5000`

## API Endpoints

### Get Home
- **GET** `/` - Welcome message

### Get All Items
- **GET** `/api/items` - Retrieve all items

### Get Single Item
- **GET** `/api/items/<id>` - Retrieve a specific item by ID

### Create Item
- **POST** `/api/items` - Create a new item
  - Request body: `{"name": "Item name", "description": "Item description"}`

### Update Item
- **PUT** `/api/items/<id>` - Update an existing item
  - Request body: `{"name": "Updated name", "description": "Updated description"}`

### Delete Item
- **DELETE** `/api/items/<id>` - Delete an item

## Example Usage

```bash
# Get all items
curl http://localhost:5000/api/items

# Create a new item
curl -X POST http://localhost:5000/api/items \
  -H "Content-Type: application/json" \
  -d '{"name": "New Item", "description": "A new item"}'

# Get a specific item
curl http://localhost:5000/api/items/1

# Update an item
curl -X PUT http://localhost:5000/api/items/1 \
  -H "Content-Type: application/json" \
  -d '{"name": "Updated Item"}'

# Delete an item
curl -X DELETE http://localhost:5000/api/items/1
```
