#!/usr/bin/env python3
"""
Repository Documentation Generator
Scans code repositories and generates comprehensive markdown documentation
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
import subprocess
import re

class RepoDocGenerator:
    def __init__(self, repo_path, output_dir="docs"):
        self.repo_path = Path(repo_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.file_extensions = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.java': 'Java',
            '.go': 'Go',
            '.rb': 'Ruby',
            '.php': 'PHP',
            '.sh': 'Shell',
            '.yaml': 'YAML',
            '.yml': 'YAML',
            '.json': 'JSON',
            '.tf': 'Terraform',
            '.dockerfile': 'Dockerfile',
            'Dockerfile': 'Dockerfile',
        }
        
        self.ignore_patterns = [
            '__pycache__', 'node_modules', '.git', 'venv', 'env',
            '.pytest_cache', 'dist', 'build', '.egg-info', 'target'
        ]
    
    def should_ignore(self, path):
        """Check if path should be ignored"""
        path_str = str(path)
        return any(pattern in path_str for pattern in self.ignore_patterns)
    
    def get_git_info(self):
        """Extract git repository information"""
        try:
            os.chdir(self.repo_path)
            
            # Get repo URL
            url = subprocess.check_output(['git', 'config', '--get', 'remote.origin.url'], 
                                         stderr=subprocess.DEVNULL).decode().strip()
            
            # Get current branch
            branch = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                                            stderr=subprocess.DEVNULL).decode().strip()
            
            # Get last commit
            last_commit = subprocess.check_output(['git', 'log', '-1', '--pretty=format:%H - %s (%an, %ar)'],
                                                 stderr=subprocess.DEVNULL).decode().strip()
            
            # Get contributors
            contributors = subprocess.check_output(['git', 'log', '--format=%an', '--all'],
                                                  stderr=subprocess.DEVNULL).decode().strip().split('\n')
            unique_contributors = len(set(contributors))
            
            return {
                'url': url,
                'branch': branch,
                'last_commit': last_commit,
                'contributors': unique_contributors
            }
        except:
            return None
    
    def scan_directory_structure(self):
        """Scan and document directory structure"""
        structure = []
        
        for root, dirs, files in os.walk(self.repo_path):
            # Filter out ignored directories
            dirs[:] = [d for d in dirs if not self.should_ignore(Path(root) / d)]
            
            level = root.replace(str(self.repo_path), '').count(os.sep)
            indent = '  ' * level
            folder_name = os.path.basename(root)
            
            if level > 0:
                structure.append(f"{indent}📁 {folder_name}/")
            
            sub_indent = '  ' * (level + 1)
            for file in sorted(files):
                if not file.startswith('.'):
                    structure.append(f"{sub_indent}📄 {file}")
        
        return '\n'.join(structure[:100])  # Limit to first 100 items
    
    def analyze_code_files(self):
        """Analyze code files and extract information"""
        file_stats = {}
        total_lines = 0
        
        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if not self.should_ignore(Path(root) / d)]
            
            for file in files:
                file_path = Path(root) / file
                ext = file_path.suffix.lower()
                
                # Check for Dockerfile
                if file.lower() == 'dockerfile':
                    ext = 'Dockerfile'
                
                if ext in self.file_extensions or file in self.file_extensions:
                    lang = self.file_extensions.get(ext, self.file_extensions.get(file, 'Unknown'))
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = len(f.readlines())
                            total_lines += lines
                            
                            if lang not in file_stats:
                                file_stats[lang] = {'files': 0, 'lines': 0}
                            
                            file_stats[lang]['files'] += 1
                            file_stats[lang]['lines'] += lines
                    except:
                        pass
        
        return file_stats, total_lines
    
    def extract_functions_and_classes(self, file_path):
        """Extract function and class definitions from Python files"""
        functions = []
        classes = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
                # Extract functions
                func_pattern = r'def\s+(\w+)\s*\((.*?)\):'
                for match in re.finditer(func_pattern, content):
                    func_name = match.group(1)
                    params = match.group(2)
                    functions.append(f"`{func_name}({params})`")
                
                # Extract classes
                class_pattern = r'class\s+(\w+)(?:\(.*?\))?:'
                for match in re.finditer(class_pattern, content):
                    class_name = match.group(1)
                    classes.append(f"`{class_name}`")
        except:
            pass
        
        return functions, classes
    
    def find_readme(self):
        """Find and read README file"""
        readme_files = ['README.md', 'README.txt', 'README.rst', 'README']
        
        for readme in readme_files:
            readme_path = self.repo_path / readme
            if readme_path.exists():
                try:
                    with open(readme_path, 'r', encoding='utf-8', errors='ignore') as f:
                        return f.read()
                except:
                    pass
        return None
    
    def find_dependencies(self):
        """Find dependency files and extract information"""
        deps = {}
        
        # Python dependencies
        requirements = self.repo_path / 'requirements.txt'
        if requirements.exists():
            try:
                with open(requirements, 'r') as f:
                    deps['Python (requirements.txt)'] = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            except:
                pass
        
        # Node dependencies
        package_json = self.repo_path / 'package.json'
        if package_json.exists():
            try:
                with open(package_json, 'r') as f:
                    data = json.load(f)
                    if 'dependencies' in data:
                        deps['Node.js (package.json)'] = list(data['dependencies'].keys())
            except:
                pass
        
        # Go dependencies
        go_mod = self.repo_path / 'go.mod'
        if go_mod.exists():
            deps['Go (go.mod)'] = ['See go.mod file']
        
        return deps
    
    def find_config_files(self):
        """Find configuration files"""
        config_patterns = [
            'config.*', '*.config.*', '.env*', 'docker-compose.*',
            'Dockerfile*', '*.yaml', '*.yml', '*.json', '*.tf'
        ]
        
        configs = []
        for pattern in config_patterns:
            for file in self.repo_path.glob(pattern):
                if file.is_file() and not self.should_ignore(file):
                    configs.append(file.name)
        
        return sorted(set(configs))
    
    def generate_documentation(self):
        """Generate complete markdown documentation"""
        print(f"📚 Scanning repository: {self.repo_path}")
        
        # Gather information
        git_info = self.get_git_info()
        file_stats, total_lines = self.analyze_code_files()
        structure = self.scan_directory_structure()
        readme_content = self.find_readme()
        dependencies = self.find_dependencies()
        configs = self.find_config_files()
        
        # Generate markdown
        doc = []
        
        # Header
        repo_name = self.repo_path.name
        doc.append(f"# {repo_name} Documentation\n")
        doc.append(f"*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
        doc.append("---\n")
        
        # Repository Information
        if git_info:
            doc.append("## 📦 Repository Information\n")
            doc.append(f"- **Repository URL:** {git_info['url']}")
            doc.append(f"- **Current Branch:** `{git_info['branch']}`")
            doc.append(f"- **Last Commit:** {git_info['last_commit']}")
            doc.append(f"- **Contributors:** {git_info['contributors']}")
            doc.append("\n---\n")
        
        # Project Overview (from README if exists)
        if readme_content:
            doc.append("## 📖 Project Overview\n")
            doc.append(readme_content[:1000])  # First 1000 chars
            if len(readme_content) > 1000:
                doc.append("\n\n*[README truncated - see full README.md]*")
            doc.append("\n\n---\n")
        
        # Code Statistics
        doc.append("## 📊 Code Statistics\n")
        doc.append(f"**Total Lines of Code:** {total_lines:,}\n")
        doc.append("### Languages Used\n")
        
        if file_stats:
            doc.append("| Language | Files | Lines |")
            doc.append("|----------|-------|-------|")
            for lang, stats in sorted(file_stats.items(), key=lambda x: x[1]['lines'], reverse=True):
                doc.append(f"| {lang} | {stats['files']} | {stats['lines']:,} |")
        else:
            doc.append("No code files found.")
        
        doc.append("\n---\n")
        
        # Directory Structure
        doc.append("## 📁 Directory Structure\n")
        doc.append("```")
        doc.append(structure)
        doc.append("```\n")
        doc.append("---\n")
        
        # Dependencies
        if dependencies:
            doc.append("## 📦 Dependencies\n")
            for dep_type, dep_list in dependencies.items():
                doc.append(f"### {dep_type}\n")
                if len(dep_list) <= 20:
                    for dep in dep_list:
                        doc.append(f"- {dep}")
                else:
                    for dep in dep_list[:20]:
                        doc.append(f"- {dep}")
                    doc.append(f"\n*...and {len(dep_list) - 20} more*")
                doc.append("")
            doc.append("---\n")
        
        # Configuration Files
        if configs:
            doc.append("## ⚙️ Configuration Files\n")
            for config in configs[:30]:
                doc.append(f"- `{config}`")
            if len(configs) > 30:
                doc.append(f"\n*...and {len(configs) - 30} more*")
            doc.append("\n---\n")
        
        # Key Python Files (if Python project)
        if 'Python' in file_stats:
            doc.append("## 🐍 Python Modules\n")
            py_files = []
            for root, dirs, files in os.walk(self.repo_path):
                dirs[:] = [d for d in dirs if not self.should_ignore(Path(root) / d)]
                for file in files:
                    if file.endswith('.py') and not file.startswith('__'):
                        file_path = Path(root) / file
                        rel_path = file_path.relative_to(self.repo_path)
                        functions, classes = self.extract_functions_and_classes(file_path)
                        
                        if functions or classes:
                            py_files.append({
                                'path': str(rel_path),
                                'functions': functions[:10],
                                'classes': classes[:10]
                            })
            
            for py_file in py_files[:10]:  # Limit to 10 files
                doc.append(f"### `{py_file['path']}`\n")
                if py_file['classes']:
                    doc.append("**Classes:**")
                    doc.append(', '.join(py_file['classes']))
                    doc.append("")
                if py_file['functions']:
                    doc.append("**Functions:**")
                    doc.append(', '.join(py_file['functions'][:5]))
                    doc.append("")
            
            doc.append("---\n")
        
        # Setup Instructions
        doc.append("## 🚀 Getting Started\n")
        doc.append("### Prerequisites\n")
        
        if 'Python' in file_stats:
            doc.append("- Python 3.x")
        if 'Node.js (package.json)' in dependencies:
            doc.append("- Node.js and npm")
        if 'Go (go.mod)' in dependencies:
            doc.append("- Go 1.x")
        
        doc.append("\n### Installation\n")
        doc.append("```bash")
        doc.append("# Clone the repository")
        if git_info:
            doc.append(f"git clone {git_info['url']}")
        doc.append(f"cd {repo_name}\n")
        
        if 'Python (requirements.txt)' in dependencies:
            doc.append("# Install Python dependencies")
            doc.append("pip install -r requirements.txt\n")
        
        if 'Node.js (package.json)' in dependencies:
            doc.append("# Install Node dependencies")
            doc.append("npm install\n")
        
        doc.append("```\n")
        doc.append("---\n")
        
        # Footer
        doc.append("## 📝 Notes\n")
        doc.append("This documentation was automatically generated. For more detailed information, ")
        doc.append("please refer to inline comments in the source code and any additional documentation files.\n")
        
        return '\n'.join(doc)
    
    def save_documentation(self):
        """Generate and save documentation"""
        doc_content = self.generate_documentation()
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = self.output_dir / f"{self.repo_path.name}_documentation.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(doc_content)
        
        print(f"✅ Documentation generated: {output_file}")
        return output_file


def main():
    parser = argparse.ArgumentParser(
        description='Generate markdown documentation from repository code',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python repo_doc_generator.py /path/to/repo
  python repo_doc_generator.py . -o documentation
  python repo_doc_generator.py ~/projects/myapp --output ./docs
        """
    )
    
    parser.add_argument('repo_path', help='Path to the repository to document')
    parser.add_argument('-o', '--output', default='docs', 
                       help='Output directory for documentation (default: docs)')
    
    args = parser.parse_args()
    
    repo_path = Path(args.repo_path).resolve()
    
    if not repo_path.exists():
        print(f"❌ Error: Repository path does not exist: {repo_path}")
        sys.exit(1)
    
    if not repo_path.is_dir():
        print(f"❌ Error: Path is not a directory: {repo_path}")
        sys.exit(1)
    
    print("=" * 60)
    print("Repository Documentation Generator")
    print("=" * 60)
    
    generator = RepoDocGenerator(repo_path, args.output)
    output_file = generator.save_documentation()
    
    print("\n" + "=" * 60)
    print(f"📄 View documentation: {output_file}")
    print("=" * 60)


if __name__ == '__main__':
    main()
