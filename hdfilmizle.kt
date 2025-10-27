package com.keyiflerolsun

import com.lagradost.cloudstream3.*
import com.lagradost.cloudstream3.utils.*
import org.jsoup.Jsoup
import org.jsoup.nodes.Element
import com.lagradost.nicehttp.Requests
import com.lagradost.cloudstream3.plugins.CloudstreamPlugin
import com.lagradost.cloudstream3.plugins.Plugin
import android.content.Context
import java.net.URI

class Hdfilmizle : MainAPI() {
    override var mainUrl = "https://www.hdfilmizle.to"
    override var name = "Hdfilmizle - Latte"
    override val supportedTypes = setOf(TvType.Movie, TvType.TvSeries)
    override val hasMainPage = true
    override val hasQuickSearch = true
    override val hasDownloadSupport = true
    override val hasChromecastSupport = false

    override suspend fun getMainPage(page: Int, request: MainPageRequest): HomePageResponse {
        val document = app.get(mainUrl).document
        val home = ArrayList<HomePageList>()

        // Popüler Filmler
        val popularMovies = document.select("div.movies:contains(Popüler Filmler) article.movie").mapNotNull { element ->
            val title = element.selectFirst("h2 a")?.text() ?: return@mapNotNull null
            val href = element.selectFirst("h2 a")?.attr("href") ?: return@mapNotNull null
            val poster = element.selectFirst("img")?.attr("data-src") ?: element.selectFirst("img")?.attr("src")
            MovieSearchResponse(
                name = title,
                url = fixUrl(href),
                posterUrl = fixUrl(poster ?: ""),
                type = TvType.Movie
            )
        }
        if (popularMovies.isNotEmpty()) {
            home.add(HomePageList("Popüler Filmler", popularMovies))
        }

        // Yeni Eklenen Filmler
        val newMovies = document.select("div.movies:contains(Yeni Eklenen Filmler) article.movie").mapNotNull { element ->
            val title = element.selectFirst("h2 a")?.text() ?: return@mapNotNull null
            val href = element.selectFirst("h2 a")?.attr("href") ?: return@mapNotNull null
            val poster = element.selectFirst("img")?.attr("data-src") ?: element.selectFirst("img")?.attr("src")
            MovieSearchResponse(
                name = title,
                url = fixUrl(href),
                posterUrl = fixUrl(poster ?: ""),
                type = TvType.Movie
            )
        }
        if (newMovies.isNotEmpty()) {
            home.add(HomePageList("Yeni Eklenen Filmler", newMovies))
        }

        // Diziler
        val series = document.select("div.movies:contains(Diziler) article.movie").mapNotNull { element ->
            val title = element.selectFirst("h2 a")?.text() ?: return@mapNotNull null
            val href = element.selectFirst("h2 a")?.attr("href") ?: return@mapNotNull null
            val poster = element.selectFirst("img")?.attr("data-src") ?: element.selectFirst("img")?.attr("src")
            MovieSearchResponse(
                name = title,
                url = fixUrl(href),
                posterUrl = fixUrl(poster ?: ""),
                type = TvType.TvSeries
            )
        }
        if (series.isNotEmpty()) {
            home.add(HomePageList("Diziler", series))
        }

        return HomePageResponse(home)
    }

    override suspend fun search(query: String): List<SearchResponse> {
        val searchUrl = "$mainUrl/ara"
        val document = app.get(searchUrl, params = mapOf("q" to query)).document
        
        return document.select("article.movie").mapNotNull { element ->
            val title = element.selectFirst("h2 a")?.text() ?: return@mapNotNull null
            val href = element.selectFirst("h2 a")?.attr("href") ?: return@mapNotNull null
            val poster = element.selectFirst("img")?.attr("data-src") ?: element.selectFirst("img")?.attr("src")
            val yearText = element.selectFirst("span.year")?.text()
            val year = yearText?.filter { it.isDigit() }?.toIntOrNull()
            
            val type = when {
                title.contains("Sezon") || title.contains("Bölüm") || href.contains("/dizi/") -> TvType.TvSeries
                else -> TvType.Movie
            }
            
            MovieSearchResponse(
                name = title,
                url = fixUrl(href),
                posterUrl = fixUrl(poster ?: ""),
                year = year,
                type = type
            )
        }
    }

    override suspend fun load(url: String): LoadResponse {
        val document = app.get(url).document
        
        val title = document.selectFirst("h1.title")?.text() ?: ""
        val poster = document.selectFirst("div.poster img")?.attr("src") ?: ""
        val description = document.selectFirst("div.description")?.text() ?: ""
        
        val yearText = document.selectFirst("span.year")?.text()
        val year = yearText?.filter { it.isDigit() }?.toIntOrNull()
        
        val ratingText = document.selectFirst("span.imdb")?.text()
        val rating = ratingText?.toRatingInt()
        
        val actors = document.select("div.actors a").map { it.text().trim() }
        val tags = document.select("div.genres a").map { it.text().trim() }
        
        val recommendations = document.select("div.recommendations article.movie, div.similar-movies article.movie").mapNotNull { element ->
            val recTitle = element.selectFirst("h3 a, h4 a")?.text() ?: return@mapNotNull null
            val recHref = element.selectFirst("a")?.attr("href") ?: return@mapNotNull null
            val recPoster = element.selectFirst("img")?.attr("src") ?: element.selectFirst("img")?.attr("data-src") ?: ""
            
            MovieSearchResponse(
                name = recTitle,
                url = fixUrl(recHref),
                posterUrl = fixUrl(recPoster)
            )
        }

        val isSeries = url.contains("/dizi/") || title.contains("Sezon") || title.contains("Bölüm")
        
        return if (isSeries) {
            newTvSeriesLoadResponse(title, url, TvType.TvSeries) {
                this.posterUrl = fixUrl(poster)
                this.year = year
                this.plot = description
                this.rating = rating
                this.tags = tags
                this.actors = actors
                this.recommendations = recommendations
                
                // Bölümleri çek
                val episodes = document.select("div.episodes a").mapNotNull { epElement ->
                    val epName = epElement.text().trim()
                    val epUrl = epElement.attr("href")
                    if (epName.isNotBlank() && epUrl.isNotBlank()) {
                        Episode(epUrl, epName)
                    } else null
                }
                this.episodes = episodes
            }
        } else {
            newMovieLoadResponse(title, url, TvType.Movie, "") {
                this.posterUrl = fixUrl(poster)
                this.year = year
                this.plot = description
                this.rating = rating
                this.tags = tags
                this.actors = actors
                this.recommendations = recommendations
            }
        }
    }

    override suspend fun loadLinks(
        data: String,
        isCasting: Boolean,
        subtitleCallback: (SubtitleFile) -> Unit,
        callback: (ExtractorLink) -> Unit
    ): Boolean {
        val document = app.get(data).document
        
        // Video iframe'lerini bul
        val iframes = document.select("iframe[src]")
        var foundLinks = false
        
        iframes.forEach { iframe ->
            val src = iframe.attr("src")
            if (src.isNotBlank()) {
                val fixedSrc = fixUrl(src)
                loadExtractor(fixedSrc, mainUrl, subtitleCallback, callback)
                foundLinks = true
            }
        }
        
        // Alternatif olarak video tag'larını kontrol et
        val videoTags = document.select("video source[src]")
        videoTags.forEach { video ->
            val src = video.attr("src")
            if (src.isNotBlank()) {
                callback(
                    ExtractorLink(
                        name,
                        "Direct",
                        fixUrl(src),
                        mainUrl,
                        Qualities.Unknown.value,
                        false
                    )
                )
                foundLinks = true
            }
        }
        
        return foundLinks
    }

    private fun String.toRatingInt(): Int? {
        return try {
            (this.toFloat() * 10).toInt()
        } catch (e: Exception) {
            null
        }
    }

    private fun fixUrl(url: String): String {
        return when {
            url.startsWith("//") -> "https:$url"
            url.startsWith("/") -> "$mainUrl$url"
            else -> url
        }
    }
}

class HdfilmizlePlugin : CloudstreamPlugin() {
    override fun load(context: Context) {
        registerMainAPI(Hdfilmizle())
    }
}

@Suppress("UNUSED_PARAMETER")
fun loadPlugin(context: Context): Plugin {
    return HdfilmizlePlugin()
}