import { useCallback, useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import {
  ArrowUpRight,
  BookOpenText,
  CalendarDays,
  FileSearch,
  Search,
  ShieldCheck,
  Sparkles,
} from 'lucide-react'

import {
  api,
  type KnowledgeDocument,
  type KnowledgeSearchResponse,
} from '../api'
import {
  Button,
  Card,
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  SectionTitle,
} from '../components'
import { formatDate } from '../utils'

function getKnowledgeCatalog() {
  return api.knowledgeCatalog()
}

export function KnowledgePage() {
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([])
  const [query, setQuery] = useState('')
  const [result, setResult] = useState<KnowledgeSearchResponse | null>(null)
  const [loadingCatalog, setLoadingCatalog] = useState(true)
  const [loadingSearch, setLoadingSearch] = useState(false)
  const [catalogError, setCatalogError] = useState('')
  const [searchError, setSearchError] = useState('')

  const loadCatalog = useCallback(async () => {
    setLoadingCatalog(true)
    setCatalogError('')
    try {
      const response = await getKnowledgeCatalog()
      setDocuments(response.items)
    } catch (issue) {
      setCatalogError(
        issue instanceof Error ? issue.message : 'Knowledge articles failed to load.',
      )
    } finally {
      setLoadingCatalog(false)
    }
  }, [])

  useEffect(() => {
    let active = true
    void getKnowledgeCatalog().then(
      (response) => {
        if (active) setDocuments(response.items)
      },
      (issue: unknown) => {
        if (active) {
          setCatalogError(
            issue instanceof Error
              ? issue.message
              : 'Knowledge articles failed to load.',
          )
        }
      },
    ).finally(() => {
      if (active) setLoadingCatalog(false)
    })
    return () => {
      active = false
    }
  }, [])

  async function search(queryText: string) {
    const trimmed = queryText.trim()
    if (!trimmed) return
    setLoadingSearch(true)
    setSearchError('')
    setResult(null)
    try {
      setResult(await api.searchKnowledge(trimmed))
    } catch (issue) {
      setSearchError(
        issue instanceof Error ? issue.message : 'Knowledge search failed.',
      )
    } finally {
      setLoadingSearch(false)
    }
  }

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    void search(query)
  }

  const hasSearched = result !== null || loadingSearch || Boolean(searchError)

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="SELF-SERVICE"
        title="Knowledge base"
        description="Search fictional troubleshooting articles and review their cited guidance."
        action={
          <span className="demo-label"><ShieldCheck size={14} /> Fictional demo articles</span>
        }
      />

      <Card className="knowledge-search-card">
        <div className="knowledge-search-intro">
          <span className="knowledge-search-icon"><BookOpenText size={22} /></span>
          <div>
            <h2>What can we help you solve?</h2>
            <p>Search across {documents.length || 'the'} support articles.</p>
          </div>
        </div>
        <form className="knowledge-search-form" onSubmit={submitSearch}>
          <Search size={19} />
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Try “VPN connection keeps dropping”"
            aria-label="Search knowledge base"
            maxLength={1000}
            required
          />
          <Button type="submit" disabled={loadingSearch || !query.trim()}>
            {loadingSearch ? 'Searching…' : 'Search'}
          </Button>
        </form>
        <p className="knowledge-hint">
          <Sparkles size={14} /> Matches are ranked by raw cosine similarity, not probability.
        </p>
      </Card>

      {searchError && <ErrorState message={searchError} onRetry={() => void search(query)} />}
      {loadingSearch && <LoadingState label="Searching the knowledge base" />}
      {result && (
        <section className="knowledge-results">
          <div className="knowledge-results-heading">
            <div>
              <p className="eyebrow">SEARCH RESULTS</p>
              <h2>Matches for “{query}”</h2>
              <p>
                {result.matches.length} ranked chunk{result.matches.length === 1 ? '' : 's'} ·{' '}
                {result.state.replaceAll('_', ' ')}
              </p>
            </div>
            <button
              type="button"
              className="text-link"
              onClick={() => {
                setResult(null)
                setSearchError('')
              }}
            >
              Clear results
            </button>
          </div>
          {result.state === 'no_documents' ? (
            <EmptyState
              title="No documents indexed"
              description="The knowledge catalog is empty. Add fictional articles and restart the backend to reindex."
            />
          ) : result.state === 'no_reliable_match' ? (
            <div className="no-match-banner">
              <FileSearch size={20} />
              <div>
                <strong>No reliable match found</strong>
                <p>
                  The search returned no evidence above the retrieval threshold. ResolveIQ
                  will not invent troubleshooting instructions.
                </p>
              </div>
            </div>
          ) : (
            <div className="knowledge-result-list">
              {result.matches.map((match, index) => (
                <Card className="knowledge-result-card" key={match.chunk_id}>
                  <div className="knowledge-result-top">
                    <span className="result-rank">#{index + 1}</span>
                    <span className="knowledge-category">{match.category}</span>
                    <span className="result-score">
                      {match.similarity_score.toFixed(3)} <small>cosine similarity</small>
                    </span>
                  </div>
                  <h3>{match.title}</h3>
                  <div className="result-meta">
                    <span><FileSearch size={14} /> {match.document_id}</span>
                    <span><CalendarDays size={14} /> Revised {formatDate(match.revision_date)}</span>
                  </div>
                  <div className="article-content">{match.content}</div>
                  <div className="article-source">
                    <span>Source: {match.source_reference}</span>
                    <span>Chunk {match.chunk_id}</span>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </section>
      )}

      {!hasSearched && (
        <section className="knowledge-catalog">
          <SectionTitle
            title="Browse all articles"
            subtitle="Select an article to search for its relevant troubleshooting content."
            action={loadingCatalog ? undefined : <span className="catalog-count">{documents.length} articles</span>}
          />
          {catalogError ? (
            <ErrorState
              message={catalogError}
              onRetry={() => void loadCatalog()}
            />
          ) : loadingCatalog ? (
            <LoadingState label="Loading articles" />
          ) : documents.length === 0 ? (
            <EmptyState
              title="No articles available"
              description="Knowledge articles will appear here when the backend index is available."
              action={
                <Button variant="secondary" className="mt-4" onClick={() => void loadCatalog()}>
                  Retry
                </Button>
              }
            />
          ) : (
            <div className="knowledge-catalog-grid">
              {documents.map((document) => (
                <button
                  type="button"
                  className="catalog-item"
                  key={document.document_id}
                  onClick={() => {
                    setQuery(document.title)
                    void search(document.title)
                  }}
                >
                  <span className="catalog-item-icon"><BookOpenText size={17} /></span>
                  <span className="catalog-item-content">
                    <strong>{document.title}</strong>
                    <small>{document.category} · revised {formatDate(document.revision_date)}</small>
                    <small className="catalog-source">{document.source_reference}</small>
                  </span>
                  <ArrowUpRight size={16} className="catalog-arrow" />
                </button>
              ))}
            </div>
          )}
        </section>
      )}
    </div>
  )
}
