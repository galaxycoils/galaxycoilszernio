import os
import subprocess
import json
import re

def analyze():
    os.makedirs('logs', exist_ok=True)
    
    try:
        result = subprocess.run(['zernio', 'analytics:posts', '--limit', '100'], capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
    except Exception as e:
        print(f"Error running zernio analytics:posts: {e}")
        if isinstance(e, subprocess.CalledProcessError):
            print(f"Stderr: {e.stderr}")
        return

    posts = data.get('posts', [])
    
    categories = {
        'Empty': {'er': [], 'views': []},
        'CTA/Question': {'er': [], 'views': []},
        'Legacy': {'er': [], 'views': []},
        'Value': {'er': [], 'views': []},
        'Other': {'er': [], 'views': []}
    }
    
    for post in posts:
        content = post.get('content', '') or ''
        
        # Remove hashtags to check for empty
        text_no_hashtags = re.sub(r'#\w+', '', content).strip()
        
        cat = 'Other'
        content_lower = content.lower()
        
        if not text_no_hashtags:
            cat = 'Empty'
        elif any(k in content_lower for k in ['?', '👇', 'vote', 'rate']):
            cat = 'CTA/Question'
        elif 'day ' in content_lower:
            cat = 'Legacy'
        elif any(k in content_lower for k in ['save', 'tip', 'saas', 'workflow']):
            cat = 'Value'
            
        analytics = post.get('analytics', {})
        er = analytics.get('engagementRate') or 0
        views = analytics.get('views') or 0
        
        categories[cat]['er'].append(er)
        categories[cat]['views'].append(views)

    report_path = 'logs/engagement-report.md'
    with open(report_path, 'w') as f:
        f.write('# Engagement Report\n\n')
        f.write('| Category | Avg ER | Avg Views | Post Count |\n')
        f.write('|---|---|---|---|\n')
        
        for cat in ['Empty', 'CTA/Question', 'Legacy', 'Value', 'Other']:
            metrics = categories[cat]
            count = len(metrics['er'])
            avg_er = sum(metrics['er']) / count if count > 0 else 0
            avg_views = sum(metrics['views']) / count if count > 0 else 0
            f.write(f'| {cat} | {avg_er:.2f} | {avg_views:.1f} | {count} |\n')
            
    print(f"Report written to {report_path}")

if __name__ == '__main__':
    analyze()
