import sys
import os
import sqlite3
import random
import re
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QTextEdit, QFileDialog, 
                             QSpinBox, QMessageBox, QWidget, QDialog)
from PyQt5.QtCore import Qt

class TriviaQuizDatabase:
    def __init__(self, db_path='trivia_quiz.db'):
        """Initialize database for tracking quiz performance"""
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self._create_tables()

    def _create_tables(self):
        """Create necessary database tables"""
        # Questions table to store generated questions
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY,
                question TEXT UNIQUE,
                source_file TEXT,
                total_attempts INTEGER DEFAULT 0,
                correct_attempts INTEGER DEFAULT 0
            )
        ''')
        
        # Quiz history table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS quiz_history (
                id INTEGER PRIMARY KEY,
                date DATETIME DEFAULT CURRENT_TIMESTAMP,
                total_questions INTEGER,
                correct_questions INTEGER,
                source_file TEXT
            )
        ''`)
        self.conn.commit()

    def insert_or_update_question(self, question, source_file):
        """Insert or update question in the database"""
        try:
            self.cursor.execute('''
                INSERT OR IGNORE INTO questions 
                (question, source_file) VALUES (?, ?)
            ''', (question, source_file))
            self.conn.commit()
        except sqlite3.IntegrityError:
            print(f"Question already exists: {question}")

    def record_quiz_result(self, total_questions, correct_questions, source_file):
        """Record quiz result in history"""
        self.cursor.execute('''
            INSERT INTO quiz_history 
            (total_questions, correct_questions, source_file) 
            VALUES (?, ?, ?)
        ''', (total_questions, correct_questions, source_file))
        self.conn.commit()

    def update_question_stats(self, question, is_correct):
        """Update question statistics"""
        self.cursor.execute('''
            UPDATE questions 
            SET total_attempts = total_attempts + 1,
                correct_attempts = correct_attempts + ?
            WHERE question = ?
        ''', (1 if is_correct else 0, question))
        self.conn.commit()

    def get_challenging_questions(self, limit=5):
        """Retrieve questions with lowest correct rate"""
        self.cursor.execute('''
            SELECT question FROM questions 
            WHERE total_attempts > 0
            ORDER BY (correct_attempts * 1.0 / total_attempts) ASC
            LIMIT ?
        ''', (limit,))
        return [row[0] for row in self.cursor.fetchall()]

class QuestionGenerator:
    @staticmethod
    def generate_trivia_questions(file_path):
        """Generate trivia questions from a text file"""
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Basic question generation strategies
        questions = []
        
        # Generate "What" questions
        what_questions = [
            f"What {sentence}?" 
            for sentence in re.findall(r'[A-Z][^.!?]*', content) 
            if len(sentence.split()) > 4
        ][:10]
        questions.extend(what_questions)
        
        # Generate "Why" questions
        why_questions = [
            f"Why is {sentence}?" 
            for sentence in re.findall(r'[A-Z][^.!?]*', content) 
            if len(sentence.split()) > 5
        ][:10]
        questions.extend(why_questions)
        
        # Generate "How" questions
        how_questions = [
            f"How does {sentence}?" 
            for sentence in re.findall(r'[A-Z][^.!?]*', content) 
            if len(sentence.split()) > 5
        ][:10]
        questions.extend(how_questions)
        
        return list(set(questions))  # Remove duplicates

class TriviaQuizApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Trivia Quiz Generator")
        self.setGeometry(100, 100, 600, 500)
        
        self.database = TriviaQuizDatabase()
        self.current_questions = []
        self.current_answers = {}
        self.current_source_file = None
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the main user interface"""
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        
        # File Selection
        file_layout = QHBoxLayout()
        self.file_label = QLabel("No file selected")
        select_file_btn = QPushButton("Select Source File")
        select_file_btn.clicked.connect(self.select_source_file)
        file_layout.addWidget(self.file_label)
        file_layout.addWidget(select_file_btn)
        
        # Number of Questions Selector
        question_count_layout = QHBoxLayout()
        question_count_label = QLabel("Number of Questions:")
        self.question_count_spinbox = QSpinBox()
        self.question_count_spinbox.setRange(1, 20)
        self.question_count_spinbox.setValue(5)
        question_count_layout.addWidget(question_count_label)
        question_count_layout.addWidget(self.question_count_spinbox)
        
        # Generate Quiz Button
        generate_quiz_btn = QPushButton("Generate Quiz")
        generate_quiz_btn.clicked.connect(self.generate_quiz)
        
        # Question Display Area
        self.question_display = QTextEdit()
        self.question_display.setReadOnly(True)
        
        # Answer Input
        self.answer_input = QTextEdit()
        self.answer_input.setPlaceholderText("Type your answer here...")
        
        # Submit Button
        submit_btn = QPushButton("Submit Answers")
        submit_btn.clicked.connect(self.submit_answers)
        
        # Challenging Questions Button
        challenging_btn = QPushButton("Show Challenging Questions")
        challenging_btn.clicked.connect(self.show_challenging_questions)
        
        # Add Widgets to Layout
        main_layout.addLayout(file_layout)
        main_layout.addLayout(question_count_layout)
        main_layout.addWidget(generate_quiz_btn)
        main_layout.addWidget(QLabel("Quiz Questions:"))
        main_layout.addWidget(self.question_display)
        main_layout.addWidget(QLabel("Your Answers:"))
        main_layout.addWidget(self.answer_input)
        main_layout.addWidget(submit_btn)
        main_layout.addWidget(challenging_btn)
        
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
    
    def select_source_file(self):
        """Open file dialog to select source file"""
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Source File", "", "Text Files (*.txt)")
        if file_path:
            self.current_source_file = file_path
            self.file_label.setText(os.path.basename(file_path))
    
    def generate_quiz(self):
        """Generate quiz questions from source file"""
        if not self.current_source_file:
            QMessageBox.warning(self, "Error", "Please select a source file first!")
            return
        
        num_questions = self.question_count_spinbox.value()
        
        # Generate questions
        questions = QuestionGenerator.generate_trivia_questions(self.current_source_file)
        
        # Randomly select questions
        self.current_questions = random.sample(questions, min(num_questions, len(questions)))
        
        # Display questions
        self.question_display.setText("\n\n".join(self.current_questions))
        
        # Store questions in database
        for question in self.current_questions:
            self.database.insert_or_update_question(question, self.current_source_file)
    
    def submit_answers(self):
        """Process submitted answers"""
        user_answers = self.answer_input.toPlainText().split('\n')
        
        # Basic scoring (placeholder - could be enhanced with NLP)
        correct_count = 0
        
        result_text = "Quiz Results:\n"
        for i, (question, user_answer) in enumerate(zip(self.current_questions, user_answers), 1):
            is_correct = len(user_answer.strip()) > 0  # Placeholder logic
            
            if is_correct:
                correct_count += 1
            
            # Update question statistics in database
            self.database.update_question_stats(question, is_correct)
            
            result_text += f"{i}. {question}\nYour Answer: {user_answer}\n{'Correct' if is_correct else 'Incorrect'}\n\n"
        
        # Record quiz result
        self.database.record_quiz_result(len(self.current_questions), correct_count, self.current_source_file)
        
        # Show results
        QMessageBox.information(self, "Quiz Results", 
                                f"You got {correct_count} out of {len(self.current_questions)} questions correct!")
    
    def show_challenging_questions(self):
        """Display historically challenging questions"""
        challenging_questions = self.database.get_challenging_questions()
        
        if not challenging_questions:
            QMessageBox.information(self, "Challenging Questions", "No challenging questions found yet.")
            return
        
        challenge_dialog = QDialog(self)
        challenge_dialog.setWindowTitle("Challenging Questions")
        challenge_layout = QVBoxLayout()
        
        for question in challenging_questions:
            label = QLabel(question)
            label.setWordWrap(True)
            challenge_layout.addWidget(label)
        
        challenge_dialog.setLayout(challenge_layout)
        challenge_dialog.exec_()

def main():
    app = QApplication(sys.argv)
    trivia_app = TriviaQuizApp()
    trivia_app.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
