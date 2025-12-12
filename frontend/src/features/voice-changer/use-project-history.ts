import { useState, useEffect, useCallback } from 'react'

export interface Project {
  id: string
  filename: string
  taskId: string
  mode: 'ai' | 'simple'
  pitchShift: number
  status: 'completed' | 'error'
  createdAt: string
}

const STORAGE_KEY = 'voice_changer_projects'
const MAX_PROJECTS = 20

function loadProjects(): Project[] {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored) {
      return JSON.parse(stored)
    }
  } catch (error) {
    console.error('Failed to load projects:', error)
  }
  return []
}

function saveProjects(projects: Project[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(projects))
  } catch (error) {
    console.error('Failed to save projects:', error)
  }
}

export function useProjectHistory() {
  const [projects, setProjects] = useState<Project[]>(() => loadProjects())

  useEffect(() => {
    saveProjects(projects)
  }, [projects])

  const addProject = useCallback(
    (data: Omit<Project, 'id' | 'createdAt'>) => {
      const newProject: Project = {
        ...data,
        id: crypto.randomUUID(),
        createdAt: new Date().toISOString(),
      }

      setProjects((prev) => {
        const updated = [newProject, ...prev]
        // Keep only the latest MAX_PROJECTS
        return updated.slice(0, MAX_PROJECTS)
      })
    },
    []
  )

  const deleteProject = useCallback((id: string) => {
    setProjects((prev) => prev.filter((p) => p.id !== id))
  }, [])

  const clearProjects = useCallback(() => {
    setProjects([])
  }, [])

  return {
    projects,
    addProject,
    deleteProject,
    clearProjects,
  }
}
