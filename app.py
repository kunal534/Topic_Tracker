from flask import Flask, request, jsonify, render_template_string
from database_manager import DatabaseManager
from crawlers.reddit_crawler import RedditCrawler
from crawlers.youtube_crawler import YouTubeCrawler
from crawlers.google_crawler import GoogleCrawler
from summary_generator import SummaryGenerator
from task_scheduler import TaskScheduler
from config import Config
import logging
import os
from datetime import datetime
from bson import ObjectId

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize components
try:
    # Database
    db_manager = DatabaseManager(Config.MONGODB_URI)
    
    # Crawlers
    reddit_crawler = RedditCrawler(
        Config.REDDIT_CLIENT_ID,
        Config.REDDIT_CLIENT_SECRET,
        Config.REDDIT_USER_AGENT
    ) if all([Config.REDDIT_CLIENT_ID, Config.REDDIT_CLIENT_SECRET]) else None

    youtube_crawler = YouTubeCrawler(
        Config.RAPIDAPI_KEY_YOUTUBE
    ) if Config.RAPIDAPI_KEY_YOUTUBE else None

    google_crawler = GoogleCrawler(
        Config.RAPIDAPI_KEY_GOOGLE
    ) if Config.RAPIDAPI_KEY_GOOGLE else None

    crawlers = {
        'reddit': reddit_crawler,
        'youtube': youtube_crawler,
        'google': google_crawler
    }

    # Summary generator (GPT via RapidAPI)
    summary_generator = SummaryGenerator(
        api_key=Config.RAPIDAPI_KEY_GPT
    ) if Config.RAPIDAPI_KEY_GPT else None

    # Task scheduler
    if summary_generator:
        scheduler = TaskScheduler(db_manager, crawlers, summary_generator)
        scheduler.start()
    else:
        scheduler = None
        logger.error("Cannot start scheduler: No valid GPT API key provided")

    logger.info("Application initialized successfully")

except Exception as e:
    logger.error(f"Error initializing application: {e}")
    raise

# Helper function to convert ObjectId to string
def serialize_doc(doc):
    """Convert MongoDB document to JSON serializable format"""
    if doc is None:
        return None
    if isinstance(doc, list):
        return [serialize_doc(item) for item in doc]
    if isinstance(doc, dict):
        for key, value in doc.items():
            if isinstance(value, ObjectId):
                doc[key] = str(value)
            elif isinstance(value, datetime):
                doc[key] = value.isoformat()
            elif isinstance(value, (dict, list)):
                doc[key] = serialize_doc(value)
    return doc

# Web Interface Route
@app.route('/')
def index():
    """Simple web interface"""
    html_template = '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Content Aggregator</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 800px; margin: 0 auto; }
            .form-group { margin: 15px 0; }
            label { display: block; margin-bottom: 5px; font-weight: bold; }
            input, select { width: 100%; padding: 8px; margin-bottom: 10px; }
            button { background: #007bff; color: white; padding: 10px 20px; border: none; cursor: pointer; }
            button:hover { background: #0056b3; }
            .task-list { margin-top: 30px; }
            .task-item { border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px; }
            .status { padding: 20px; background: #f8f9fa; border-radius: 5px; margin: 20px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Content Aggregator</h1>
            
            <div class="status">
                <h3>System Status</h3>
                <p>Scheduler: <span id="scheduler-status">Loading...</span></p>
                <p>Active Tasks: <span id="active-tasks">Loading...</span></p>
            </div>
            
            <div class="form-group">
                <h3>Create New Task</h3>
                <form id="create-task-form">
                    <label>User ID:</label>
                    <input type="text" id="user-id" required>
                    
                    <label>Topic:</label>
                    <input type="text" id="topic" required>
                    
                    <label>Interval (minutes):</label>
                    <select id="interval">
                        <option value="30">30 minutes</option>
                        <option value="60">1 hour</option>
                        <option value="120">2 hours</option>
                        <option value="360">6 hours</option>
                        <option value="720">12 hours</option>
                        <option value="1440">24 hours</option>
                    </select>
                    
                    <button type="submit">Create Task</button>
                </form>
            </div>
            
            <div id="tasks-list" class="task-list">
                <h3>Loading tasks...</h3>
            </div>
        </div>
        
        <script>
            // Load status
            function loadStatus() {
                fetch('/api/status')
                    .then(response => response.json())
                    .then(data => {
                        document.getElementById('scheduler-status').textContent = 
                            data.running ? 'Running' : 'Stopped';
                        document.getElementById('active-tasks').textContent = data.active_tasks;
                    })
                    .catch(error => console.error('Error loading status:', error));
            }
            
            // Load tasks
            function loadTasks() {
                fetch('/api/tasks')
                    .then(response => response.json())
                    .then(data => {
                        const tasksList = document.getElementById('tasks-list');
                        if (data.length === 0) {
                            tasksList.innerHTML = '<h3>No tasks found</h3>';
                            return;
                        }
                        
                        let html = '<h3>Active Tasks</h3>';
                        data.forEach(task => {
                            html += `
                                <div class="task-item">
                                    <h4>${task.topic}</h4>
                                    <p>User: ${task.user_id}</p>
                                    <p>Interval: ${task.interval_minutes} minutes</p>
                                    <p>Total Runs: ${task.total_runs || 0}</p>
                                    <p>Last Run: ${task.last_run ? new Date(task.last_run).toLocaleString() : 'Never'}</p>
                                    <p>Next Run: ${new Date(task.next_run).toLocaleString()}</p>
                                    <button onclick="deleteTask('${task._id}')">Delete Task</button>
                                </div>
                            `;
                        });
                        tasksList.innerHTML = html;
                    })
                    .catch(error => console.error('Error loading tasks:', error));
            }
            
            // Create task
            document.getElementById('create-task-form').addEventListener('submit', function(e) {
                e.preventDefault();
                
                const formData = {
                    user_id: document.getElementById('user-id').value,
                    topic: document.getElementById('topic').value,
                    interval_minutes: parseInt(document.getElementById('interval').value)
                };
                
                fetch('/api/tasks', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(formData)
                })
                .then(response => response.json())
                .then(data => {
                    alert('Task created successfully!');
                    document.getElementById('create-task-form').reset();
                    loadTasks();
                    loadStatus();
                })
                .catch(error => {
                    console.error('Error creating task:', error);
                    alert('Error creating task');
                });
            });
            
            // Delete task
            function deleteTask(taskId) {
                if (confirm('Are you sure you want to delete this task?')) {
                    fetch(`/api/tasks/${taskId}`, {
                        method: 'DELETE'
                    })
                    .then(response => response.json())
                    .then(data => {
                        alert('Task deleted successfully!');
                        loadTasks();
                        loadStatus();
                    })
                    .catch(error => {
                        console.error('Error deleting task:', error);
                        alert('Error deleting task');
                    });
                }
            }
            
            // Load data on page load
            loadStatus();
            loadTasks();
            
            // Refresh status every 30 seconds
            setInterval(loadStatus, 30000);
        </script>
    </body>
    </html>
    '''
    return render_template_string(html_template)

# API Routes
@app.route('/api/status')
def get_status():
    """Get system status"""
    try:
        active_tasks = db_manager.get_all_tasks()
        
        status = {
            'running': scheduler.is_running() if scheduler else False,
            'active_tasks': len(active_tasks),
            'crawlers': {
                'reddit': reddit_crawler is not None,
                'youtube': youtube_crawler is not None,
                'google': google_crawler is not None
            },
            'summary_generator': summary_generator is not None,
            'database': db_manager.is_connected()
        }
        
        return jsonify(status)
    
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """Get all tasks"""
    try:
        tasks = db_manager.get_all_tasks()
        return jsonify(serialize_doc(tasks))
    
    except Exception as e:
        logger.error(f"Error getting tasks: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks', methods=['POST'])
def create_task():
    """Create a new task"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['user_id', 'topic', 'interval_minutes']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Create task
        task_id = db_manager.create_task(
            user_id=data['user_id'],
            topic=data['topic'],
            interval_minutes=int(data['interval_minutes'])
        )
        
        # Add to scheduler if available
        if scheduler:
            scheduler.reload_tasks()
        
        return jsonify({'task_id': str(task_id), 'message': 'Task created successfully'})
    
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    """Delete a task"""
    try:
        # Convert string to ObjectId
        from bson import ObjectId
        task_id = ObjectId(task_id)
        
        # Delete task
        result = db_manager.delete_task(task_id)
        
        if result:
            # Reload scheduler tasks
            if scheduler:
                scheduler.reload_tasks()
            return jsonify({'message': 'Task deleted successfully'})
        else:
            return jsonify({'error': 'Task not found'}), 404
    
    except Exception as e:
        logger.error(f"Error deleting task: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/tasks/<task_id>', methods=['GET'])
def get_task(task_id):
    """Get a specific task"""
    try:
        from bson import ObjectId
        task_id = ObjectId(task_id)
        
        task = db_manager.get_task(task_id)
        if task:
            return jsonify(serialize_doc(task))
        else:
            return jsonify({'error': 'Task not found'}), 404
    
    except Exception as e:
        logger.error(f"Error getting task: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/summaries', methods=['GET'])
def get_summaries():
    """Get summaries for a user"""
    try:
        user_id = request.args.get('user_id')
        topic = request.args.get('topic')
        limit = int(request.args.get('limit', 10))
        
        summaries = db_manager.get_summaries(user_id=user_id, topic=topic, limit=limit)
        return jsonify(serialize_doc(summaries))
    
    except Exception as e:
        logger.error(f"Error getting summaries: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/summaries/<summary_id>', methods=['GET'])
def get_summary(summary_id):
    """Get a specific summary"""
    try:
        from bson import ObjectId
        summary_id = ObjectId(summary_id)
        
        summary = db_manager.get_summary(summary_id)
        if summary:
            return jsonify(serialize_doc(summary))
        else:
            return jsonify({'error': 'Summary not found'}), 404
    
    except Exception as e:
        logger.error(f"Error getting summary: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/crawl', methods=['POST'])
def manual_crawl():
    """Manually trigger a crawl for a topic"""
    try:
        data = request.get_json()
        topic = data.get('topic')
        sources = data.get('sources', ['reddit', 'youtube', 'google'])
        
        if not topic:
            return jsonify({'error': 'Topic is required'}), 400
        
        results = {}
        
        # Crawl from each requested source
        for source in sources:
            if source in crawlers and crawlers[source]:
                try:
                    if source == 'reddit':
                        results[source] = reddit_crawler.fetch_posts(topic, limit=25)
                    elif source == 'youtube':
                        results[source] = youtube_crawler.search_videos(topic, max_results=25)
                    elif source == 'google':
                        results[source] = google_crawler.search(topic, num_results=25)
                except Exception as e:
                    logger.error(f"Error crawling {source}: {e}")
                    results[source] = []
            else:
                results[source] = []
        
        return jsonify(results)
    
    except Exception as e:
        logger.error(f"Error in manual crawl: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate-summary', methods=['POST'])
def generate_summary():
    """Manually generate a summary"""
    try:
        data = request.get_json()
        content = data.get('content')
        topic = data.get('topic', 'General')
        
        if not content:
            return jsonify({'error': 'Content is required'}), 400
        
        if not summary_generator:
            return jsonify({'error': 'Summary generator not available'}), 503
        
        # Generate summary
        summary = summary_generator.generate_summary(content, topic)
        
        return jsonify({'summary': summary})
    
    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'components': {
                'database': db_manager.is_connected(),
                'scheduler': scheduler.is_running() if scheduler else False,
                'reddit_crawler': reddit_crawler is not None,
                'youtube_crawler': youtube_crawler is not None,
                'google_crawler': google_crawler is not None,
                'summary_generator': summary_generator is not None
            }
        }
        
        # Check if all critical components are working
        if not health_status['components']['database']:
            health_status['status'] = 'unhealthy'
        
        return jsonify(health_status)
    
    except Exception as e:
        logger.error(f"Error in health check: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(Exception)
def handle_exception(e):
    logger.error(f"Unhandled exception: {e}")
    return jsonify({'error': 'An unexpected error occurred'}), 500

# Cleanup on shutdown
@app.teardown_appcontext
def cleanup(error):
    """Cleanup resources"""
    pass

def shutdown_handler():
    """Handle application shutdown"""
    if scheduler:
        scheduler.shutdown()
    logger.info("Application shutdown complete")

# Register shutdown handler
import atexit
atexit.register(shutdown_handler)

if __name__ == '__main__':
    # Development server
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    port = int(os.getenv('PORT', 5050))
    host = os.getenv('HOST', '0.0.0.0')
    
    logger.info(f"Starting Flask app on {host}:{port} (debug={debug_mode})")
    app.run(host=host, port=port, debug=debug_mode)