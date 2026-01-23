"""Tests for input classification and spec parsing."""

import pytest

from lloyd.orchestrator.input_classifier import InputClassifier, InputType
from lloyd.orchestrator.spec_parser import SpecParser


class TestInputClassifier:
    """Tests for InputClassifier."""

    def test_short_input_is_idea(self):
        """Short input should be classified as idea."""
        classifier = InputClassifier()
        result = classifier.classify("Build a todo app")
        assert result.input_type == InputType.IDEA
        assert result.confidence >= 0.8

    def test_numbered_requirements_is_spec(self):
        """Numbered requirements should be classified as spec."""
        classifier = InputClassifier()
        spec = """# Project Spec

## Requirements

1.1 User can create accounts
1.2 User can log in with email
1.3 User can reset password

## Features

2.1 Dashboard shows statistics
2.2 Users can export data
"""
        result = classifier.classify(spec)
        assert result.input_type == InputType.SPEC
        assert result.confidence >= 0.6

    def test_req_format_is_spec(self):
        """REQ-XXX format should be classified as spec."""
        classifier = InputClassifier()
        spec = """# Requirements Document

REQ-001: System must support 1000 concurrent users
REQ-002: Response time must be under 200ms
FR-001: User can upload files
NFR-001: System must be available 99.9% of time
"""
        result = classifier.classify(spec)
        assert result.input_type == InputType.SPEC

    def test_user_story_format_is_spec(self):
        """User story format should be classified as spec."""
        classifier = InputClassifier()
        spec = """# User Stories

As a user, I want to log in so that I can access my data
As an admin, I want to manage users so that I can control access
As a user, I want to export reports so that I can analyze data offline
"""
        result = classifier.classify(spec)
        assert result.input_type == InputType.SPEC

    def test_prose_is_idea(self):
        """Prose without structure should be classified as idea."""
        classifier = InputClassifier()
        idea = """I want to build an AI-powered writing assistant that helps
authors write better content. It should use GPT-4 to suggest improvements
and catch grammatical errors. The focus should be on creative writing."""
        result = classifier.classify(idea)
        assert result.input_type == InputType.IDEA

    def test_is_spec_shorthand(self):
        """Test the is_spec() convenience method."""
        classifier = InputClassifier()
        assert not classifier.is_spec("Build a simple app")
        # Need enough lines to not trigger short-input heuristic
        spec = """# Requirements
1.1 First requirement
1.2 Second requirement
1.3 Third requirement
1.4 Fourth requirement
"""
        assert classifier.is_spec(spec)


class TestSpecParser:
    """Tests for SpecParser."""

    def test_parse_numbered_requirements(self):
        """Parse numbered requirements into structured format."""
        parser = SpecParser()
        spec = """# Todo App Spec

This is a simple todo application.

## Core Features

1.1 Users can create tasks
1.2 Users can mark tasks complete
1.3 Users can delete tasks

## Optional

2.1 Tasks have due dates
"""
        result = parser.parse(spec)
        assert result.title == "Todo App Spec"
        assert len(result.requirements) == 4
        assert result.requirements[0].id == "1.1"
        assert result.requirements[0].title == "Users can create tasks"

    def test_parse_req_format(self):
        """Parse REQ-XXX format requirements."""
        parser = SpecParser()
        spec = """# API Requirements

REQ-001: Support REST endpoints
REQ-002: Return JSON responses
FR-001: Authenticate via JWT
"""
        result = parser.parse(spec)
        assert len(result.requirements) == 3
        assert result.requirements[0].id == "REQ-001"
        assert result.requirements[2].id == "FR-001"

    def test_parse_with_acceptance_criteria(self):
        """Parse requirements with acceptance criteria."""
        parser = SpecParser()
        spec = """# Feature Spec

1.1 User login

Acceptance Criteria:
- User sees login form
- User can enter credentials
- User receives error on invalid input
"""
        result = parser.parse(spec)
        assert len(result.requirements) >= 1
        req = result.requirements[0]
        assert req.id == "1.1"
        assert len(req.acceptance_criteria) == 3

    def test_requirements_to_stories(self):
        """Convert requirements to story format."""
        parser = SpecParser()
        spec = """# Test Spec

1.1 First feature
1.2 Second feature
"""
        parsed = parser.parse(spec)
        stories = parser.requirements_to_stories(parsed)

        assert len(stories) == 2
        assert stories[0]["id"] == "1.1"
        assert stories[0]["title"] == "First feature"
        assert isinstance(stories[0]["acceptanceCriteria"], list)
        assert stories[0]["passes"] is False

    def test_priority_inference(self):
        """Test priority inference from requirement text."""
        parser = SpecParser()
        spec = """# Requirements

1.1 Users must be able to log in
1.2 Users should see dashboard
1.3 Users could export data
"""
        parsed = parser.parse(spec)
        stories = parser.requirements_to_stories(parsed)

        # "must" = priority 1
        assert stories[0]["priority"] == 1
        # "should" = priority 2
        assert stories[1]["priority"] == 2
        # "could" = priority 4
        assert stories[2]["priority"] == 4

    def test_dependency_inference(self):
        """Test dependency inference from requirement ordering."""
        parser = SpecParser()
        spec = """# Requirements

1.1 Setup database
1.2 Create user model
1.3 Build user API
"""
        parsed = parser.parse(spec)
        stories = parser.requirements_to_stories(parsed)

        # 1.2 depends on 1.1, 1.3 depends on 1.2
        assert "1.1" in stories[1]["dependencies"]
        assert "1.2" in stories[2]["dependencies"]

    def test_empty_spec_fallback_to_bullets(self):
        """If no structured requirements, fall back to bullets."""
        parser = SpecParser()
        spec = """# Feature List

- Implement user authentication
- Add file upload capability
- Create reporting dashboard
"""
        result = parser.parse(spec)
        assert len(result.requirements) == 3
        assert result.requirements[0].id == "R1"


class TestFlowIntegration:
    """Test integration with LloydFlow."""

    def test_flow_detects_idea(self):
        """Flow should detect idea input."""
        from lloyd.orchestrator.flow import LloydFlow
        from lloyd.orchestrator.input_classifier import InputType

        flow = LloydFlow()
        flow.receive_idea("Build a simple calculator app")

        assert flow.input_type == InputType.IDEA

    def test_flow_detects_spec(self):
        """Flow should detect spec input."""
        from lloyd.orchestrator.flow import LloydFlow
        from lloyd.orchestrator.input_classifier import InputType

        spec = """# Calculator Spec

1.1 Support addition
1.2 Support subtraction
1.3 Support multiplication
1.4 Support division
"""
        flow = LloydFlow()
        flow.receive_idea(spec)

        assert flow.input_type == InputType.SPEC
        assert flow.state.complexity == "spec"
