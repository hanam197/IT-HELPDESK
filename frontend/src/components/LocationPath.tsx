import { Fragment } from 'react'
import { ChevronRight } from 'lucide-react'

export function LocationPath({value}:{value:string}){
 const parts=value.split(' / ')
 return <span className="location-path" aria-label={parts.join(' › ')}>{parts.map((part,index)=><Fragment key={index}>{index>0&&<ChevronRight size={14} aria-hidden="true"/>}<span>{part}</span></Fragment>)}</span>
}
