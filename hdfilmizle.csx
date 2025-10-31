// ==CloudStreamScript==
// @name HDFilmizle
// @description HDFilmizle.to - Türkçe Dublaj ve Altyazılı Film ve Dizi İzle
// @author GitLatte
// @language tr
// @supportedSources movie, tvseries
// @homepage https://www.hdfilmizle.to
// ==/CloudStreamScript==

package com.lagradost.script

import com.lagradost.cloudstream3.*
import com.lagradost.cloudstream3.utils.*
import com.lagradost.cloudstream3.extractors.*
import com.lagradost.cloudstream3.mvvm.safeApiCall
import org.jsoup.nodes.Element
import java.util.*

class HDFilmizleScript : MainAPI() {
    override var mainUrl = "https://www.hdfilmizle.to"
    override var name = "HDFilmizle"
    override val supportedTypes = setOf(TvType.Movie, TvType.TvSeries)
    override var lang = "tr"

    // Ana sayfa için
    override suspend fun getMainPage(page: Int, request: MainPageRequest): HomePageResponse {
        val items = ArrayList<HomePageList>()
        
        try {
            val document = app.get(mainUrl).document

            // Popüler Filmler
            val popularMovies = document.select("div.tab-pane.active div.item").mapNotNull { it.toSearchResult() }
            if (popularMovies.isNotEmpty()) {
                items.add(HomePageList("Popüler Filmler", popularMovies))
            }

            // Yeni Eklenen Filmler
            val newMoviesUrl = "$mainUrl/film-izle"
            val newMoviesDoc = app.get(newMoviesUrl).document
            val newMovies = newMoviesDoc.select("div.movie-poster").mapNotNull { it.toSearchResult() }
            if (newMovies.isNotEmpty()) {
                items.add(HomePageList("Yeni Filmler", newMovies))
            }

            // Popüler Diziler
            val popularSeriesUrl = "$mainUrl/dizi-izle"
            val popularSeriesDoc = app.get(popularSeriesUrl).document
            val popularSeries = popularSeriesDoc.select("div.movie-poster").mapNotNull { it.toSearchResult() }
            if (popularSeries.isNotEmpty()) {
                items.add(HomePageList("Popüler Diziler", popularSeries))
            }

        } catch (e: Exception) {
            e.printStackTrace()
        }
        
        return HomePageResponse(items)
    }
    
    // Arama fonksiyonu
    override suspend fun search(query: String): List<SearchResponse> {
        return safeApiCall {
            val encodedQuery = java.net.URLEncoder.encode(query, "UTF-8")
            val document = app.get("$mainUrl/ara?q=$encodedQuery").document
            document.select("div.movie-poster, div.item").mapNotNull { it.toSearchResult() }
        } ?: emptyList()
    }
    
    // Detay sayfası
    override suspend fun load(url: String): LoadResponse? {
        return safeApiCall {
            val document = app.get(url).document
            
            val title = document.selectFirst("h1.film-title")?.text() ?: return@safeApiCall null
            val description = document.selectFirst("div.film-about p")?.text()
            val poster = document.selectFirst("div.film-poster img")?.attr("src")
            val year = document.selectFirst("span.film-year")?.text()?.toIntOrNull()
            val rating = document.selectFirst("span.imdb-rating")?.text()?.toRatingInt()

            // Film mi dizi mi kontrol et
            val hasSeasons = document.selectFirst("div.seasons") != null
            val episodes = document.select("div.episode-list a")

            if (!hasSeasons && episodes.isEmpty()) {
                // Film
                newMovieLoadResponse(title, url, TvType.Movie) {
                    this.posterUrl = fixUrl(poster)
                    this.plot = description
                    this.year = year
                    this.rating = rating
                }
            } else {
                // Dizi
                val episodeList = episodes.mapNotNull { episode ->
                    val episodeUrl = episode.attr("href")
                    val episodeName = episode.selectFirst("span.episode-name")?.text() ?: 
                                    "Bölüm ${episode.selectFirst("span.episode-number")?.text()}"
                    
                    newEpisode(episodeUrl) {
                        this.name = episodeName
                        this.posterUrl = fixUrl(poster)
                    }
                }

                newTvSeriesLoadResponse(title, url, TvType.TvSeries, episodeList) {
                    this.posterUrl = fixUrl(poster)
                    this.plot = description
                    this.year = year
                    this.rating = rating
                }
            }
        }
    }
    
    // Video linklerini çözme
    override suspend fun loadLinks(
        data: String,
        isCasting: Boolean,
        subtitleCallback: (SubtitleFile) -> Unit,
        callback: (ExtractorLink) -> Unit
    ): Boolean {
        return safeApiCall {
            val document = app.get(data).document
            
            // Video iframe'lerini bul
            val iframes = document.select("iframe[src]")
            iframes.forEach { iframe ->
                val iframeUrl = iframe.attr("src")
                if (iframeUrl.isNotBlank()) {
                    // Harici extractor kullan
                    loadExtractor(iframeUrl, "$mainUrl/", subtitleCallback, callback)
                }
            }

            // Alternatif video player'ları kontrol et
            val videoScripts = document.select("script:containsData(video)")
            videoScripts.forEach { script ->
                val scriptText = script.data()
                // Video URL'lerini script içinden çıkarmaya çalış
                val videoUrls = Regex("""(https?:[^"'\s]*\.(mp4|m3u8)[^"'\s]*)""").findAll(scriptText)
                videoUrls.forEach { match ->
                    val videoUrl = match.value
                    callback(
                        ExtractorLink(
                            name,
                            "Direct",
                            videoUrl,
                            "$mainUrl/",
                            Qualities.Unknown.value
                        )
                    )
                }
            }
            
            true
        } ?: false
    }
    
    // Yardımcı fonksiyonlar
    private fun Element.toSearchResult(): SearchResponse? {
        val title = this.selectFirst("img")?.attr("alt") ?: 
                   this.selectFirst("h3, h4")?.text() ?: return null
        
        val href = this.selectFirst("a")?.attr("href") ?: return null
        val posterUrl = this.selectFirst("img")?.attr("src")
        val year = this.selectFirst("span.year")?.text()?.toIntOrNull()

        // Dizi mi film mi kontrol et
        val isSeries = href.contains("/dizi/") || 
                      this.selectFirst("span.type")?.text()?.contains("dizi", true) == true ||
                      this.selectFirst("span.episodes") != null

        return if (isSeries) {
            newTvSeriesSearchResponse(title, fixUrl(href)) {
                this.posterUrl = fixUrl(posterUrl)
                this.year = year
            }
        } else {
            newMovieSearchResponse(title, fixUrl(href)) {
                this.posterUrl = fixUrl(posterUrl)
                this.year = year
            }
        }
    }

    private fun fixUrl(url: String?): String? {
        return if (url == null) {
            null
        } else if (url.startsWith("//")) {
            "https:$url"
        } else if (url.startsWith("/")) {
            "$mainUrl$url"
        } else if (!url.startsWith("http")) {
            "$mainUrl/$url"
        } else {
            url
        }
    }

    private fun String?.toRatingInt(): Int? {
        return this?.replace(",", ".")?.toFloatOrNull()?.times(10)?.toInt()
    }
}
