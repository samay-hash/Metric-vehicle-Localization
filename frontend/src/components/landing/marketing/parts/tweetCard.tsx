import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

type TweetCardProps = {
  name: string;
  handle: string;
  bio?: string;
  quote: string;
  date: string;
  likes?: string;
  tag?: string;
  href: string;
};

export function TweetCard({
  name,
  handle,
  bio,
  quote,
  date,
  likes,
  tag,
  href,
}: TweetCardProps) {
  return (
    <a href={href} target="_blank" rel="noreferrer">
      <Card>
        <CardHeader>
          <CardTitle>{name}</CardTitle>
          <CardDescription>
            {handle}
            {bio ? ` · ${bio}` : ""}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p>{quote}</p>
        </CardContent>
        <CardFooter className="flex-wrap gap-3 text-xs tracking-eyebrow text-muted-foreground uppercase">
          <span>{date}</span>
          {likes ? <span>{likes} likes</span> : null}
          {tag ? (
            <span className="border border-dashed px-2 py-0.5">{tag}</span>
          ) : null}
        </CardFooter>
      </Card>
    </a>
  );
}
