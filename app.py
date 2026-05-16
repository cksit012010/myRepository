from flask import Flask, jsonify, request
from functools import wraps
import logging
from datetime import datetime
from typing import Optional, Dict, List, Tuple
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Constants
DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 100
API_KEY = os.getenv('API_KEY', 'your-secret-key-here')

# In-memory product storage with index for better performance
products_db = [
    {"id": 1, "name": "Laptop", "price": 999.99, "stock": 50, "category": "Electronics", "created_at": datetime.now().isoformat()},
    {"id": 2, "name": "Mouse", "price": 29.99, "stock": 200, "category": "Electronics", "created_at": datetime.now().isoformat()},
    {"id": 3, "name": "Keyboard", "price": 79.99, "stock": 150, "category": "Electronics", "created_at": datetime.now().isoformat()},
    {"id": 4, "name": "Monitor", "price": 299.99, "stock": 80, "category": "Electronics", "created_at": datetime.now().isoformat()},
    {"id": 5, "name": "Headphones", "price": 149.99, "stock": 120, "category": "Electronics", "created_at": datetime.now().isoformat()},
]

# Product ID index for O(1) lookup
product_index = {product["id"]: idx for idx, product in enumerate(products_db)}


# ===================== DECORATORS =====================

def require_api_key(f):
    """Decorator to validate API key"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            api_key = request.headers.get('X-API-Key')
            if not api_key or api_key != API_KEY:
                logger.warning(f"Unauthorized access attempt: {request.remote_addr}")
                return jsonify({"error": "Unauthorized - Invalid API Key"}), 401
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in API key validation: {str(e)}")
            return jsonify({"error": "Authentication error"}), 500
    return decorated_function


def validate_json_request(f):
    """Decorator to validate JSON request"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            if not request.is_json:
                logger.warning(f"Non-JSON request from {request.remote_addr}")
                return jsonify({"error": "Content-Type must be application/json"}), 400
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error validating JSON request: {str(e)}")
            return jsonify({"error": "Request validation error"}), 400
    return decorated_function


# ===================== UTILITY FUNCTIONS =====================

def validate_pagination(page: int, page_size: int) -> Tuple[bool, Optional[Dict]]:
    """Validate pagination parameters"""
    try:
        if page < 1:
            return False, {"error": "Page number must be greater than 0"}
        if page_size < 1 or page_size > MAX_PAGE_SIZE:
            return False, {"error": f"Page size must be between 1 and {MAX_PAGE_SIZE}"}
        return True, None
    except Exception as e:
        logger.error(f"Pagination validation error: {str(e)}")
        return False, {"error": "Invalid pagination parameters"}


def validate_product_data(data: Dict) -> Tuple[bool, Optional[str]]:
    """Validate product data"""
    try:
        required_fields = ['name', 'price', 'stock', 'category']
        
        # Check required fields
        if not all(field in data for field in required_fields):
            missing = [f for f in required_fields if f not in data]
            return False, f"Missing required fields: {', '.join(missing)}"
        
        # Validate name
        if not isinstance(data['name'], str) or len(data['name'].strip()) == 0:
            return False, "Product name must be a non-empty string"
        
        # Validate price
        try:
            price = float(data['price'])
            if price < 0:
                return False, "Price cannot be negative"
        except (ValueError, TypeError):
            return False, "Price must be a valid number"
        
        # Validate stock
        try:
            stock = int(data['stock'])
            if stock < 0:
                return False, "Stock cannot be negative"
        except (ValueError, TypeError):
            return False, "Stock must be a valid integer"
        
        # Validate category
        if not isinstance(data['category'], str) or len(data['category'].strip()) == 0:
            return False, "Category must be a non-empty string"
        
        return True, None
    except Exception as e:
        logger.error(f"Product validation error: {str(e)}")
        return False, "Data validation error"


def get_next_product_id() -> int:
    """Get next available product ID efficiently"""
    try:
        return max([p["id"] for p in products_db]) + 1 if products_db else 1
    except Exception as e:
        logger.error(f"Error generating product ID: {str(e)}")
        raise


def find_product_by_id(product_id: int) -> Tuple[Optional[Dict], Optional[int]]:
    """Find product by ID with O(1) complexity using index"""
    try:
        if product_id in product_index:
            idx = product_index[product_id]
            return products_db[idx], idx
        return None, None
    except Exception as e:
        logger.error(f"Error finding product: {str(e)}")
        return None, None


def apply_filters(products: List[Dict], filters: Dict) -> List[Dict]:
    """Apply filters to products list"""
    try:
        filtered_products = products
        
        # Filter by category
        if 'category' in filters:
            category = filters['category'].lower()
            filtered_products = [p for p in filtered_products if p.get('category', '').lower() == category]
        
        # Filter by price range
        if 'min_price' in filters:
            try:
                min_price = float(filters['min_price'])
                filtered_products = [p for p in filtered_products if p.get('price', 0) >= min_price]
            except ValueError:
                logger.warning(f"Invalid min_price filter: {filters['min_price']}")
        
        if 'max_price' in filters:
            try:
                max_price = float(filters['max_price'])
                filtered_products = [p for p in filtered_products if p.get('price', 0) <= max_price]
            except ValueError:
                logger.warning(f"Invalid max_price filter: {filters['max_price']}")
        
        # Filter by stock availability
        if 'in_stock' in filters and filters['in_stock'].lower() == 'true':
            filtered_products = [p for p in filtered_products if p.get('stock', 0) > 0]
        
        # Search by name
        if 'search' in filters:
            search_term = filters['search'].lower()
            filtered_products = [p for p in filtered_products if search_term in p.get('name', '').lower()]
        
        return filtered_products
    except Exception as e:
        logger.error(f"Error applying filters: {str(e)}")
        return products


def paginate_results(items: List[Dict], page: int, page_size: int) -> Dict:
    """Paginate results with metadata"""
    try:
        total_items = len(items)
        total_pages = (total_items + page_size - 1) // page_size
        
        # Ensure page is within valid range
        page = max(1, min(page, total_pages)) if total_pages > 0 else 1
        
        # Calculate pagination
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_items = items[start_idx:end_idx]
        
        return {
            "data": paginated_items,
            "pagination": {
                "current_page": page,
                "page_size": page_size,
                "total_items": total_items,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1
            }
        }
    except Exception as e:
        logger.error(f"Error paginating results: {str(e)}")
        return {
            "data": [],
            "pagination": {
                "current_page": 1,
                "page_size": page_size,
                "total_items": 0,
                "total_pages": 0,
                "has_next": False,
                "has_previous": False
            }
        }


# ===================== ERROR HANDLERS =====================

@app.errorhandler(400)
def bad_request(error):
    logger.error(f"Bad request: {error}")
    return jsonify({"error": "Bad Request", "message": str(error)}), 400


@app.errorhandler(404)
def not_found(error):
    logger.error(f"Resource not found: {error}")
    return jsonify({"error": "Resource Not Found"}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal Server Error", "message": "An unexpected error occurred"}), 500


# ===================== ROUTES =====================

@app.route('/', methods=['GET'])
def home():
    """Home endpoint"""
    try:
        return jsonify({
            "message": "Welcome to Advanced Flask Products API",
            "version": "2.0",
            "endpoints": {
                "products": "/api/v1/products",
                "product_detail": "/api/v1/products/<id>",
                "health": "/api/v1/health"
            }
        }), 200
    except Exception as e:
        logger.error(f"Home endpoint error: {str(e)}")
        return jsonify({"error": "Internal Server Error"}), 500


@app.route('/api/v1/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "total_products": len(products_db)
        }), 200
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return jsonify({"status": "unhealthy", "error": str(e)}), 500


@app.route('/api/v1/products', methods=['GET'])
def get_products():
    """Get all products with pagination and filtering
    
    Query Parameters:
    - page: int (default: 1)
    - page_size: int (default: 10, max: 100)
    - category: str (filter by category)
    - min_price: float (minimum price filter)
    - max_price: float (maximum price filter)
    - in_stock: bool (filter only in-stock items)
    - search: str (search by product name)
    
    Headers:
    - X-API-Key: Your API key
    """
    try:
        logger.info(f"GET /api/v1/products - IP: {request.remote_addr}")
        
        # Get pagination parameters
        try:
            page = int(request.args.get('page', DEFAULT_PAGE))
            page_size = int(request.args.get('page_size', DEFAULT_PAGE_SIZE))
        except ValueError:
            return jsonify({"error": "Page and page_size must be integers"}), 400
        
        # Validate pagination
        is_valid, error = validate_pagination(page, page_size)
        if not is_valid:
            return jsonify(error), 400
        
        # Get filter parameters
        filters = {
            'category': request.args.get('category'),
            'min_price': request.args.get('min_price'),
            'max_price': request.args.get('max_price'),
            'in_stock': request.args.get('in_stock'),
            'search': request.args.get('search')
        }
        
        # Remove None filters
        filters = {k: v for k, v in filters.items() if v is not None}
        
        # Apply filters
        filtered_products = apply_filters(products_db, filters)
        
        # Paginate results
        result = paginate_results(filtered_products, page, page_size)
        
        logger.info(f"Successfully retrieved {len(result['data'])} products")
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error in get_products: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal Server Error", "details": str(e)}), 500


@app.route('/api/v1/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    """Get a single product by ID"""
    try:
        logger.info(f"GET /api/v1/products/{product_id} - IP: {request.remote_addr}")
        
        product, _ = find_product_by_id(product_id)
        
        if not product:
            logger.warning(f"Product {product_id} not found")
            return jsonify({"error": "Product not found"}), 404
        
        return jsonify(product), 200
        
    except Exception as e:
        logger.error(f"Error in get_product: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal Server Error"}), 500


@app.route('/api/v1/products', methods=['POST'])
@require_api_key
@validate_json_request
def create_product():
    """Create a new product
    
    Required headers:
    - X-API-Key: Your API key
    - Content-Type: application/json
    
    Request body:
    {
        "name": "Product Name",
        "price": 99.99,
        "stock": 100,
        "category": "Electronics"
    }
    """
    try:
        logger.info(f"POST /api/v1/products - IP: {request.remote_addr}")
        
        data = request.get_json()
        
        # Validate product data
        is_valid, error_msg = validate_product_data(data)
        if not is_valid:
            logger.warning(f"Invalid product data: {error_msg}")
            return jsonify({"error": error_msg}), 400
        
        # Create new product
        new_product = {
            "id": get_next_product_id(),
            "name": data['name'].strip(),
            "price": float(data['price']),
            "stock": int(data['stock']),
            "category": data['category'].strip(),
            "created_at": datetime.now().isoformat()
        }
        
        # Add to database
        products_db.append(new_product)
        product_index[new_product["id"]] = len(products_db) - 1
        
        logger.info(f"Product created successfully: ID {new_product['id']}")
        return jsonify(new_product), 201
        
    except Exception as e:
        logger.error(f"Error in create_product: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal Server Error"}), 500


@app.route('/api/v1/products/<int:product_id>', methods=['PUT'])
@require_api_key
@validate_json_request
def update_product(product_id):
    """Update a product
    
    Required headers:
    - X-API-Key: Your API key
    - Content-Type: application/json
    """
    try:
        logger.info(f"PUT /api/v1/products/{product_id} - IP: {request.remote_addr}")
        
        product, idx = find_product_by_id(product_id)
        
        if product is None:
            logger.warning(f"Product {product_id} not found for update")
            return jsonify({"error": "Product not found"}), 404
        
        data = request.get_json()
        
        # Validate provided data (partial update)
        if 'name' in data:
            if not isinstance(data['name'], str) or len(data['name'].strip()) == 0:
                return jsonify({"error": "Product name must be a non-empty string"}), 400
            product['name'] = data['name'].strip()
        
        if 'price' in data:
            try:
                price = float(data['price'])
                if price < 0:
                    return jsonify({"error": "Price cannot be negative"}), 400
                product['price'] = price
            except (ValueError, TypeError):
                return jsonify({"error": "Price must be a valid number"}), 400
        
        if 'stock' in data:
            try:
                stock = int(data['stock'])
                if stock < 0:
                    return jsonify({"error": "Stock cannot be negative"}), 400
                product['stock'] = stock
            except (ValueError, TypeError):
                return jsonify({"error": "Stock must be a valid integer"}), 400
        
        if 'category' in data:
            if not isinstance(data['category'], str) or len(data['category'].strip()) == 0:
                return jsonify({"error": "Category must be a non-empty string"}), 400
            product['category'] = data['category'].strip()
        
        product['updated_at'] = datetime.now().isoformat()
        
        logger.info(f"Product {product_id} updated successfully")
        return jsonify(product), 200
        
    except Exception as e:
        logger.error(f"Error in update_product: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal Server Error"}), 500


@app.route('/api/v1/products/<int:product_id>', methods=['DELETE'])
@require_api_key
def delete_product(product_id):
    """Delete a product
    
    Required headers:
    - X-API-Key: Your API key
    """
    try:
        logger.info(f"DELETE /api/v1/products/{product_id} - IP: {request.remote_addr}")
        
        product, idx = find_product_by_id(product_id)
        
        if product is None:
            logger.warning(f"Product {product_id} not found for deletion")
            return jsonify({"error": "Product not found"}), 404
        
        # Remove product
        deleted_product = products_db.pop(idx)
        
        # Rebuild index after deletion
        global product_index
        product_index = {p["id"]: i for i, p in enumerate(products_db)}
        
        logger.info(f"Product {product_id} deleted successfully")
        return jsonify({
            "message": "Product deleted successfully",
            "deleted_product": deleted_product
        }), 200
        
    except Exception as e:
        logger.error(f"Error in delete_product: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal Server Error"}), 500


@app.route('/api/v1/products/search', methods=['GET'])
def search_products():
    """Search products - Advanced search endpoint
    
    Query Parameters:
    - q: Search query (searches in name and category)
    - page: int (default: 1)
    - page_size: int (default: 10)
    """
    try:
        logger.info(f"GET /api/v1/products/search - IP: {request.remote_addr}")
        
        search_query = request.args.get('q', '').lower()
        
        if not search_query or len(search_query) < 1:
            return jsonify({"error": "Search query cannot be empty"}), 400
        
        # Get pagination parameters
        try:
            page = int(request.args.get('page', DEFAULT_PAGE))
            page_size = int(request.args.get('page_size', DEFAULT_PAGE_SIZE))
        except ValueError:
            return jsonify({"error": "Page and page_size must be integers"}), 400
        
        # Search in products
        search_results = [
            p for p in products_db 
            if search_query in p.get('name', '').lower() or 
               search_query in p.get('category', '').lower()
        ]
        
        # Paginate results
        result = paginate_results(search_results, page, page_size)
        
        logger.info(f"Search completed: found {len(search_results)} products")
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error in search_products: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal Server Error"}), 500


if __name__ == '__main__':
    logger.info("Starting Flask Products API...")
    app.run(debug=False, port=5000, host='0.0.0.0')
