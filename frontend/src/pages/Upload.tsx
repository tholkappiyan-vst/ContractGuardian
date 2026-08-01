import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDropzone } from 'react-dropzone'
import { Upload as UploadIcon, File, X, CheckCircle } from 'lucide-react'
import { api } from '@/lib/api'

export function Upload() {
  const [files, setFiles] = useState<File[]>([])
  const [title, setTitle] = useState('')
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const onDrop = useCallback((accepted: File[]) => {
    setFiles(prev => [...prev, ...accepted].slice(0, 10))
    if (!title && accepted[0]) {
      setTitle(accepted[0].name.replace(/\.[^.]+$/, ''))
    }
  }, [title])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'image/png': ['.png'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/tiff': ['.tiff'],
    },
    maxSize: 50 * 1024 * 1024,
  })

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index))
  }

  const handleUpload = async () => {
    if (!files.length || !title) return
    setUploading(true)
    setError('')
    try {
      const formData = new FormData()
      formData.append('file', files[0])
      formData.append('title', title)
      const contract = await api.uploadContract(formData)

      // Auto-trigger analysis
      await api.triggerAnalysis(contract.id)
      navigate(`/analysis/${contract.id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Upload Contract</h1>
        <p className="text-gray-500 mt-1">Upload a PDF, DOCX, or image of your contract for AI analysis.</p>
      </div>

      {/* Title */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1.5">Contract Title</label>
        <input
          type="text" value={title} onChange={e => setTitle(e.target.value)}
          className="input" placeholder="e.g., Employment Agreement - Acme Corp"
        />
      </div>

      {/* Dropzone */}
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors ${
          isDragActive ? 'border-brand-500 bg-brand-50' : 'border-gray-300 hover:border-brand-400 hover:bg-gray-50'
        }`}
      >
        <input {...getInputProps()} />
        <UploadIcon className="w-12 h-12 text-gray-400 mx-auto mb-4" />
        <p className="text-lg font-medium text-gray-700">
          {isDragActive ? 'Drop your contract here' : 'Drag & drop your contract'}
        </p>
        <p className="text-sm text-gray-500 mt-2">or click to browse. PDF, DOCX, PNG, JPG, TIFF (max 50MB)</p>
      </div>

      {/* File list */}
      {files.length > 0 && (
        <div className="card divide-y divide-gray-100">
          {files.map((file, i) => (
            <div key={i} className="flex items-center justify-between px-4 py-3">
              <div className="flex items-center gap-3">
                <File className="w-5 h-5 text-brand-600" />
                <div>
                  <p className="text-sm font-medium text-gray-900">{file.name}</p>
                  <p className="text-xs text-gray-500">{(file.size / 1024 / 1024).toFixed(1)} MB</p>
                </div>
              </div>
              <button onClick={() => removeFile(i)} className="p-1 hover:bg-gray-100 rounded">
                <X className="w-4 h-4 text-gray-400" />
              </button>
            </div>
          ))}
        </div>
      )}

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">{error}</div>
      )}

      {/* Upload button */}
      <button
        onClick={handleUpload}
        disabled={!files.length || !title || uploading}
        className="btn-primary w-full py-3 text-lg flex items-center justify-center gap-2"
      >
        {uploading ? (
          <>
            <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
            Analyzing...
          </>
        ) : (
          <>
            <CheckCircle className="w-5 h-5" /> Upload & Analyze
          </>
        )}
      </button>

      <p className="text-xs text-gray-500 text-center">
        Your documents are encrypted and never used for AI training. Analysis typically takes 30-60 seconds.
      </p>
    </div>
  )
}
