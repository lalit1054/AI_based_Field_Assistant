import { useQuery } from '@tanstack/react-query'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { SkeletonBlock } from '@/components/feedback/SkeletonBlock'
import { listKbDocuments } from '@/features/kb/api/documents'

export function KbPage() {
  const { data: documents, isLoading } = useQuery({
    queryKey: ['kb', 'documents'],
    queryFn: listKbDocuments,
  })

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-xl font-semibold">Knowledge base</h1>
      {isLoading ? (
        <SkeletonBlock />
      ) : (
        <div className="flex flex-col gap-2">
          {documents?.map((document) => (
            <Card key={document.id}>
              <CardContent className="flex flex-col gap-1 pt-4">
                <div className="flex items-start justify-between gap-2">
                  <p className="font-medium">{document.title}</p>
                  <Badge variant="outline">{document.doc_type.replace('_', ' ')}</Badge>
                </div>
                <p className="text-muted-foreground text-sm">
                  {document.chunk_count} chunks indexed
                </p>
              </CardContent>
            </Card>
          ))}
          {documents?.length === 0 && (
            <p className="text-muted-foreground text-sm">No documents yet.</p>
          )}
        </div>
      )}
    </div>
  )
}
