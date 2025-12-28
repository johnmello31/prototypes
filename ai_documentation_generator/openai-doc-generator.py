#!/usr/bin/env python3
"""
AI-Powered Repository Documentation Generator (OpenAI Version)
Uses OpenAI GPT API to generate intelligent descriptions and summaries
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
import subprocess
import re
from openai import OpenAI

class AIDocGenerator:
    def __init__(self, repo_path, output_dir="docs", api_key=None):
        self.repo_path = Path(repo_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize OpenAI API
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY')
        if not self.api_key:
            print("⚠️  No API key found. Running without AI features.")
            print("   Set OPENAI_API_KEY environment variable to enable AI.")
            self.client = None
        else:
            self.client = OpenAI(api_key=self.api_key)
        
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
        }
        
        self.ignore_patterns = [
            '__pycache__', 'node_modules', '.git', 'venv', 'env',
            '.pytest_cache', 'dist', 'build', '.egg-info', 'target'
        ]
    
    def should_ignore(self, path):
        """Check if path should be ignored"""
        path_str = str(path)
        return any(pattern in path_str for pattern in self.ignore_patterns)
    
    def call_gpt(self, prompt, max_tokens=1000):
        """Call OpenAI GPT API with a prompt"""
        if not self.client:
            return None
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Using GPT-4o-mini for cost efficiency
                messages=[
                    {"role": "system", "content": "You are a technical documentation expert. Provide clear, concise explanations."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"⚠️  API Error: {e}")
            return None
    
    def analyze_project_purpose(self, readme, file_stats, main_files):
        """Use AI to understand project purpose"""
        print("🤖 AI: Analyzing project purpose...")
        
        prompt = f"""Based on this repository information, provide a concise 2-3 sentence description of what this project does:

README excerpt:
{readme[:500] if readme else 'No README found'}

Languages used: {', '.join(file_stats.keys())}

Key files: {', '.join(main_files[:10])}

Provide only the description, no preamble."""

        return self.call_gpt(prompt, max_tokens=300)
    
    def generate_architecture_overview(self, structure, file_stats):
        """Use AI to describe architecture"""
        print("🤖 AI: Generating architecture overview...")
        
        prompt = f"""Analyze this project structure and describe the architecture in 3-4 sentences:

Directory structure:
{structure[:1000]}

Languages: {', '.join(file_stats.keys())}

Focus on: overall organization, separation of concerns, and key architectural patterns.
Provide only the description, no preamble."""

        return self.call_gpt(prompt, max_tokens=400)
    
    def explain_code_file(self, file_path, content_preview):
        """Use AI to explain what a code file does"""
        print(f"🤖 AI: Analyzing {file_path.name}...")
        
        prompt = f"""Explain what this code file does in 1-2 sentences:

File: {file_path.name}

Code preview:
{content_preview[:800]}

Provide only the explanation, no preamble."""

        return self.call_gpt(prompt, max_tokens=200)
    
    def generate_setup_guide(self, dependencies, file_stats):
        """Use AI to create setup instructions"""
        print("🤖 AI: Generating setup guide...")
        
        deps_text = "\n".join([f"{k}: {len(v)} packages" for k, v in dependencies.items()])
        
        prompt = f"""Create a clear, step-by-step setup guide for this project:

Languages: {', '.join(file_stats.keys())}

Dependencies:
{deps_text}

Provide numbered steps with command examples. Be concise and practical."""

        return self.call_gpt(prompt, max_tokens=600)
    
    def suggest_improvements(self, file_stats, has_tests, has_ci, has_docs):
        """Use AI to suggest project improvements"""
        print("🤖 AI: Analyzing potential improvements...")
        
        prompt = f"""Based on this project analysis, suggest 3-5 practical improvements:

Languages: {', '.join(file_stats.keys())}
Has tests: {has_tests}
Has CI/CD: {has_ci}
Has documentation: {has_docs}

Provide a bulleted list of actionable suggestions."""

        return self.call_gpt(prompt, max_tokens=400)
    
    def get_git_info(self):
        """Extract git repository information"""
        try:
            os.chdir(self.repo_path)
            
            url = subprocess.check_output(['git', 'config', '--get', 'remote.origin.url'], 
                                         stderr=subprocess.DEVNULL).decode().strip()
            branch = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                                            stderr=subprocess.DEVNULL).decode().strip()
            last_commit = subprocess.check_output(['git', 'log', '-1', '--pretty=format:%H - %s (%an, %ar)'],
                                                 stderr=subprocess.DEVNULL).decode().strip()
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
        
        return '\n'.join(structure[:100])
    
    def analyze_code_files(self):
        """Analyze code files and extract information"""
        file_stats = {}
        total_lines = 0
        main_files = []
        
        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if not self.should_ignore(Path(root) / d)]
            
            for file in files:
                file_path = Path(root) / file
                ext = file_path.suffix.lower()
                
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
                            
                            if lines > 50:
                                main_files.append(str(file_path.relative_to(self.repo_path)))
                    except:
                        pass
        
        return file_stats, total_lines, main_files
    
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
        
        requirements = self.repo_path / 'requirements.txt'
        if requirements.exists():
            try:
                with open(requirements, 'r') as f:
                    deps['Python (requirements.txt)'] = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            except:
                pass
        
        package_json = self.repo_path / 'package.json'
        if package_json.exists():
            try:
                with open(package_json, 'r') as f:
                    data = json.load(f)
                    if 'dependencies' in data:
                        deps['Node.js (package.json)'] = list(data['dependencies'].keys())
            except:
                pass
        
        return deps
    
    def check_project_health(self):
        """Check for tests, CI/CD, and documentation"""
        has_tests = any((self.repo_path / p).exists() for p in ['tests', 'test', '__tests__', 'spec'])
        has_ci = any((self.repo_path / p).exists() for p in ['.github/workflows', '.gitlab-ci.yml', '.circleci', 'Jenkinsfile'])
        has_docs = any((self.repo_path / p).exists() for p in ['docs', 'documentation', 'README.md'])
        
        return has_tests, has_ci, has_docs
    
    def analyze_key_files(self):
        """Analyze key code files with AI"""
        analyses = {}
        
        for file in ['app.py', 'main.py', 'run.py', '__init__.py', 'server.py', 'index.js', 'main.go']:
            file_path = self.repo_path / file
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        if self.client and len(content) > 100:
                            explanation = self.explain_code_file(file_path, content)
                            if explanation:
                                analyses[file] = explanation
                except:
                    pass
        
        return analyses
    
    def generate_documentation(self):
        """Generate complete AI-enhanced markdown documentation"""
        print(f"📚 Scanning repository: {self.repo_path}")
        
        # Gather information
        git_info = self.get_git_info()
        file_stats, total_lines, main_files = self.analyze_code_files()
        structure = self.scan_directory_structure()
        readme_content = self.find_readme()
        dependencies = self.find_dependencies()
        has_tests, has_ci, has_docs = self.check_project_health()
        
        # AI-powered analysis
        project_purpose = None
        architecture = None
        setup_guide = None
        improvements = None
        file_analyses = {}
        
        if self.client:
            project_purpose = self.analyze_project_purpose(readme_content, file_stats, main_files)
            architecture = self.generate_architecture_overview(structure, file_stats)
            setup_guide = self.generate_setup_guide(dependencies, file_stats)
            improvements = self.suggest_improvements(file_stats, has_tests, has_ci, has_docs)
            file_analyses = self.analyze_key_files()
        
        # Generate markdown
        doc = []
        
        repo_name = self.repo_path.name
        doc.append(f"# {repo_name} Documentation\n")
        doc.append(f"*AI-Enhanced Documentation - Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
        doc.append("---\n")
        
        if project_purpose:
            doc.append("## 🎯 What This Project Does\n")
            doc.append(project_purpose)
            doc.append("\n---\n")
        
        if git_info:
            doc.append("## 📦 Repository Information\n")
            doc.append(f"- **Repository URL:** {git_info['url']}")
            doc.append(f"- **Current Branch:** `{git_info['branch']}`")
            doc.append(f"- **Last Commit:** {git_info['last_commit']}")
            doc.append(f"- **Contributors:** {git_info['contributors']}")
            doc.append("\n---\n")
        
        doc.append("## 📊 Code Statistics\n")
        doc.append(f"**Total Lines of Code:** {total_lines:,}\n")
        doc.append("### Languages Used\n")
        
        if file_stats:
            doc.append("| Language | Files | Lines |")
            doc.append("|----------|-------|-------|")
            for lang, stats in sorted(file_stats.items(), key=lambda x: x[1]['lines'], reverse=True):
                doc.append(f"| {lang} | {stats['files']} | {stats['lines']:,} |")
        
        doc.append("\n---\n")
        
        if architecture:
            doc.append("## 🏗️ Architecture Overview\n")
            doc.append(architecture)
            doc.append("\n---\n")
        
        doc.append("## 📁 Directory Structure\n")
        doc.append("```")
        doc.append(structure)
        doc.append("```\n")
        doc.append("---\n")
        
        if file_analyses:
            doc.append("## 🔍 Key Files Analysis\n")
            for file, explanation in file_analyses.items():
                doc.append(f"### `{file}`\n")
                doc.append(explanation)
                doc.append("")
            doc.append("---\n")
        
        if dependencies:
            doc.append("## 📦 Dependencies\n")
            for dep_type, dep_list in dependencies.items():
                doc.append(f"### {dep_type}\n")
                for dep in dep_list[:20]:
                    doc.append(f"- {dep}")
                if len(dep_list) > 20:
                    doc.append(f"\n*...and {len(dep_list) - 20} more*")
                doc.append("")
            doc.append("---\n")
        
        if setup_guide:
            doc.append("## 🚀 Getting Started\n")
            doc.append(setup_guide)
            doc.append("\n---\n")
        
        doc.append("## 🏥 Project Health\n")
        doc.append(f"- **Tests:** {'✅ Yes' if has_tests else '❌ No'}")
        doc.append(f"- **CI/CD:** {'✅ Yes' if has_ci else '❌ No'}")
        doc.append(f"- **Documentation:** {'✅ Yes' if has_docs else '❌ No'}")
        doc.append("\n---\n")
        
        if improvements:
            doc.append("## 💡 Suggested Improvements\n")
            doc.append(improvements)
            doc.append("\n---\n")
        
        doc.append("## 📝 Notes\n")
        doc.append("This documentation was automatically generated using AI-powered analysis. ")
        doc.append("AI-generated sections are based on code structure and patterns. ")
        doc.append("Please verify all suggestions and descriptions.\n")
        
        return '\n'.join(doc)
    
    def save_documentation(self):
        """Generate and save documentation"""
        doc_content = self.generate_documentation()
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        output_file = self.output_dir / f"{self.repo_path.name}_AI_documentation.md"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(doc_content)
        
        print(f"✅ Documentation generated: {output_file}")
        return output_file


def main():
    parser = argparse.ArgumentParser(
        description='Generate AI-enhanced markdown documentation using OpenAI GPT',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python openai_doc_generator.py /path/to/repo
  python openai_doc_generator.py . -o documentation
  python openai_doc_generator.py ~/projects/myapp --api-key YOUR_KEY

Environment Variables:
  OPENAI_API_KEY - Your OpenAI API key for AI features
        """
    )
    
    parser.add_argument('repo_path', help='Path to the repository to document')
    parser.add_argument('-o', '--output', default='docs', 
                       help='Output directory for documentation (default: docs)')
    parser.add_argument('--api-key', help='OpenAI API key (or set OPENAI_API_KEY env var)')
    
    args = parser.parse_args()
    
    repo_path = Path(args.repo_path).resolve()
    
    if not repo_path.exists():
        print(f"❌ Error: Repository path does not exist: {repo_path}")
        sys.exit(1)
    
    if not repo_path.is_dir():
        print(f"❌ Error: Path is not a directory: {repo_path}")
        sys.exit(1)
    
    print("=" * 60)
    print("AI-Powered Repository Documentation Generator (OpenAI)")
    print("=" * 60)
    
    generator = AIDocGenerator(repo_path, args.output, args.api_key)
    output_file = generator.save_documentation()
    
    print("\n" + "=" * 60)
    print(f"📄 View documentation: {output_file}")
    print("=" * 60)


if __name__ == '__main__':
    main()
